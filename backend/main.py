from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from fastapi import WebSocket, WebSocketDisconnect

from datetime import datetime
import secrets
import itertools

import redis
import json
import threading

import asyncio

from threading import Lock
connections_lock = Lock()


# ===== Redis =====
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

# ===== async event loop =====

loop: asyncio.AbstractEventLoop | None = None

# ===== Redis Subscriber =====
def redis_subscriber():
    pubsub = redis_client.pubsub()
    pubsub.subscribe("project-events")

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        data = json.loads(message["data"])
        project_id = data["project_id"]

        with connections_lock:
            conns = list(PROJECT_CONNECTIONS.get(project_id, set()))
        for ws in conns:
            asyncio.run_coroutine_threadsafe(ws.send_json(data), loop)

# ===== backend.main:app =====
app = FastAPI()

# ===== 서버 시작 시 실행 =====
@app.on_event("startup")
async def start_redis_listener():
    global loop
    loop = asyncio.get_running_loop()

    # 블로킹 'Redis 클라이언트'를 이벤트 루프 밖으로 치움(스레드로)
    t = threading.Thread(target=redis_subscriber, daemon=True)
    t.start()

# ===== static 라우트 별도 관리 =====
app.mount(
    "/static",
    StaticFiles(directory="frontend", html=True),
    name="frontend"
)


# ===== 구조 분리 중 =====

def delete_event_service(
    project_id: int,
    event_id: int,
    user: str
):
    for i, e in enumerate(PROJECT_EVENTS):
        if e["id"] == event_id and e["project_id"] == project_id:

            if not any(
                m for m in PROJECT_MEMBERS
                if m["project_id"] == project_id and m["user"] == user
            ):
                raise HTTPException(403, "Not a project member")

            PROJECT_EVENTS.pop(i)

            redis_client.publish(
                "project-events",
                json.dumps({
                    "type": "event_deleted",
                    "project_id": project_id,
                    "event_id": event_id
                })
            )

            return {"msg": "Deleted"}

    raise HTTPException(404, "Event not found")

def update_event_service(
    project_id: int,
    event_id: int,
    title: str,
    date: str,
    version: int,
    user: str
):
    for e in PROJECT_EVENTS:
        if e["id"] == event_id and e["project_id"] == project_id:

            if not any(
                m for m in PROJECT_MEMBERS
                if m["project_id"] == project_id and m["user"] == user
            ):
                raise HTTPException(403, "Not a project member")

            if e["version"] != version:
                raise HTTPException(
                    409,
                    detail="Conflict: event has been modified by another user"
                )

            e["title"] = title
            e["date"] = date
            e["version"] += 1

            redis_client.publish(
                "project-events",
                json.dumps({
                    "type": "event_updated",
                    "project_id": project_id,
                    "event_id": event_id
                })
            )

            return e

    raise HTTPException(404, "Event not found")

def create_event_service(
    project_id: int,
    title: str,
    date: str,
    user: str
):
    # 권한 확인
    if not any(
        m for m in PROJECT_MEMBERS
        if m["project_id"] == project_id and m["user"] == user
    ):
        raise HTTPException(403, "Not a project member")

    event = {
        "id": next(event_id_seq),
        "project_id": project_id,
        "title": title,
        "date": date,
        "owner": user,
        "version": 1
    }
    PROJECT_EVENTS.append(event)

    redis_client.publish(
        "project-events",
        json.dumps({
            "type": "event_created",
            "project_id": project_id,
            "event": event
        })
    )

    return event


# ===== html 파일 직접 제공 =====
@app.get("/")
def index():
    return FileResponse("frontend/index.html")

# ===== 임시 저장소 (나중에 DB로 교체) =====
USERS = {}      # username -> password
TOKENS = {}     # token -> username

MEMOS = []      # {id, text, created_at, owner}
memo_id_seq = itertools.count(1)

# ===== Day 7: Project Space =====
PROJECTS = []         # {id, name, owner}
PROJECT_MEMBERS = []  # {project_id, user, role}
PROJECT_EVENTS = []   # {id, project_id, title, date, owner}

project_id_seq = itertools.count(1)
event_id_seq = itertools.count(1)

# ===== Day 8: WebSocket Connections =====
PROJECT_CONNECTIONS = {}  # project_id -> set of WebSocket
# 프로젝트마다 연결된 클라이언트 목록을 관리
# 실시간의 “방(Room)” 역할

# ===== 회원가입 =====
@app.post("/signup")
def signup(username: str, password: str):
    if username in USERS:
        raise HTTPException(status_code=400, detail="이미 존재하는 사용자")
    USERS[username] = password
    return {"msg": "회원가입 완료"}

# ===== 로그인 =====
@app.post("/login")
def login(username: str, password: str):
    if USERS.get(username) != password:
        raise HTTPException(status_code=401, detail="로그인 실패")
    token = secrets.token_hex(16)
    TOKENS[token] = username
    return {"token": token}

# ===== 로그인 확인 도우미 =====
def require_user(token: str | None):
    if not token or token not in TOKENS:
        raise HTTPException(status_code=401, detail="로그인 필요")
    return TOKENS[token]

# =========================================================
# =============== Day 8 Live Sync (websocket) =============
# =========================================================

@app.websocket("/ws/projects/{project_id}") # 웹소켓 핸들러
async def project_ws(
    websocket: WebSocket,
    project_id: int,
    token: str
):
    # 1. 인증
    user = require_user(token)

    # 2. 프로젝트 멤버 확인
    if not any(
        m for m in PROJECT_MEMBERS
        if m["project_id"] == project_id and m["user"] == user
    ):
        await websocket.close(code=1008)
        return

    await websocket.accept()

    # 3. 연결 등록
    with connections_lock:
        PROJECT_CONNECTIONS.setdefault(project_id, set()).add(websocket)
    try:
        while True:
            # 우리는 아직 웹소켓으로는
            # 클라이언트 메시지를 안 받는다 (읽기 전용)
            # CPU 점유 x, 비동기 대기
            await websocket.receive_text() 
            # 메세지 처리 용이 아닌 클라이언트가 연결을 끊을때까지
            # 서버가 살아 있으라고 기다리는 장치 
            # (웹소켓 핸들러 종료 방지!)
            # “메시지를 받으려고” 있는 게 아니라
            # “연결이 살아 있는 동안 서버를 잠들게 하려는 코드”
    except WebSocketDisconnect: # 클라이언트가 연결 끊으면 예외 발생
        pass
    finally:
        with connections_lock:
            conns = PROJECT_CONNECTIONS.get(project_id)
            if conns and websocket in conns:
                conns.remove(websocket)

# =========================================================
# ===================== Day 7 Project Space ===============
# =========================================================

# ===== 프로젝트 생성 =====
@app.post("/projects")
def create_project(
    name: str,
    authorization: str | None = Header(default=None)
):
    user = require_user(authorization)

    project = {
        "id": next(project_id_seq),
        "name": name,
        "owner": user
    }
    PROJECTS.append(project)

    # 생성자는 자동 멤버
    PROJECT_MEMBERS.append({
        "project_id": project["id"],
        "user": user,
        "role": "owner"   # Day 7++
    })

    return project

# ===== 내가 속한 프로젝트 목록 =====
@app.get("/projects")
def list_projects(authorization: str | None = Header(default=None)):
    user = require_user(authorization)

    my_project_ids = {
        m["project_id"]
        for m in PROJECT_MEMBERS
        if m["user"] == user
    }

    return [p for p in PROJECTS if p["id"] in my_project_ids]

# ===== 프로젝트 멤버 추가 (소유자만) =====
@app.post("/projects/{project_id}/members")
def add_project_member(
    project_id: int,
    target_user: str,
    authorization: str | None = Header(default=None)
):
    user = require_user(authorization)

    my_role = next(
        (m["role"] for m in PROJECT_MEMBERS
         if m["project_id"] == project_id and m["user"] == user),
        None
    )

    if my_role != "owner":
        raise HTTPException(403, "Only owner can add members")

    PROJECT_MEMBERS.append({
        "project_id": project_id,
        "user": target_user,
        "role": "member"
    })

    return {"msg": "Member added"}

# ===== 프로젝트 멤버 조회 =====
@app.get("/projects/{project_id}/members")
def list_project_members(
    project_id: int,
    authorization: str | None = Header(default=None)
):
    user = require_user(authorization)

    if not any(
        m for m in PROJECT_MEMBERS
        if m["project_id"] == project_id and m["user"] == user
    ):
        raise HTTPException(403, "Not a project member")

    return [
        m for m in PROJECT_MEMBERS
        if m["project_id"] == project_id
    ]

# ===== 프로젝트 일정 생성 =====
@app.post("/projects/{project_id}/events")
async def create_project_event(
    project_id: int,
    title: str,
    date: str,
    authorization: str | None = Header(default=None)
):
    user = require_user(authorization)
    return create_event_service(project_id, title, date, user)

# ===== 프로젝트 일정 조회 =====
@app.get("/projects/{project_id}/events")
def list_project_events(
    project_id: int,
    authorization: str | None = Header(default=None)
):
    user = require_user(authorization)

    if not any(
        m for m in PROJECT_MEMBERS
        if m["project_id"] == project_id and m["user"] == user
    ):
        raise HTTPException(403, "Not a project member")

    return [
        e for e in PROJECT_EVENTS
        if e["project_id"] == project_id
    ]

# ===== 프로젝트 일정 수정 =====
@app.put("/projects/{project_id}/events/{event_id}")
async def update_project_event(
    project_id: int,
    event_id: int,
    title: str,
    date: str,
    version: int,
    authorization: str | None = Header(default=None)
):
    user = require_user(authorization)
    return update_event_service(
        project_id, event_id, title, date, version, user
    )


# ===== 프로젝트 일정 삭제 =====
@app.delete("/projects/{project_id}/events/{event_id}")
async def delete_project_event(
    project_id: int,
    event_id: int,
    authorization: str | None = Header(default=None)
):
    user = require_user(authorization)
    return delete_event_service(project_id, event_id, user)


# =========================================================
# ===================== 메모 ==============================
# =========================================================

@app.post("/memo")
def create_memo(text: str, authorization: str | None = Header(default=None)):
    user = require_user(authorization)
    memo = {
        "id": next(memo_id_seq),
        "text": text,
        "created_at": datetime.utcnow().isoformat(),
        "owner": user
    }
    MEMOS.append(memo)
    return memo

@app.get("/memo")
def list_memos(authorization: str | None = Header(default=None)):
    user = require_user(authorization)
    return [m for m in MEMOS if m["owner"] == user]

@app.delete("/memo/{memo_id}")
def delete_memo(
    memo_id: int,
    authorization: str | None = Header(default=None)
):
    user = require_user(authorization)

    for i, m in enumerate(MEMOS):
        if m["id"] == memo_id:
            if m["owner"] != user:
                raise HTTPException(status_code=403, detail="권한 없음")
            MEMOS.pop(i)
            return {"msg": "삭제됨"}

    raise HTTPException(status_code=404, detail="메모 없음")

@app.put("/memo/{memo_id}")
def update_memo(
    memo_id: int,
    text: str,
    authorization: str | None = Header(default=None)
):
    user = require_user(authorization)

    for m in MEMOS:
        if m["id"] == memo_id:
            if m["owner"] != user:
                raise HTTPException(status_code=403, detail="권한 없음")
            m["text"] = text
            return m

    raise HTTPException(status_code=404, detail="메모 없음")