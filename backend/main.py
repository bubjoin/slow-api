from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from datetime import datetime
import secrets
import itertools

# ===== backend.main:app =====
app = FastAPI()

# ===== static 라우트 별도 관리 =====
app.mount(
    "/static",
    StaticFiles(directory="frontend", html=True),
    name="frontend"
)

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
PROJECT_MEMBERS = []  # {project_id, user}
PROJECT_EVENTS = []   # {id, project_id, title, date, owner}

project_id_seq = itertools.count(1)
event_id_seq = itertools.count(1)

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
def create_project_event(
    project_id: int,
    title: str,
    date: str,
    authorization: str | None = Header(default=None)
):
    user = require_user(authorization)

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
        "owner": user
    }
    PROJECT_EVENTS.append(event)
    return event

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
def update_project_event(
    project_id: int,
    event_id: int,
    title: str,
    date: str,
    authorization: str | None = Header(default=None)
):
    user = require_user(authorization)

    for e in PROJECT_EVENTS:
        if e["id"] == event_id and e["project_id"] == project_id:
            if e["owner"] != user:
                raise HTTPException(403, "No permission")
            e["title"] = title
            e["date"] = date
            return e

    raise HTTPException(404, "Event not found")

# ===== 프로젝트 일정 삭제 =====
@app.delete("/projects/{project_id}/events/{event_id}")
def delete_project_event(
    project_id: int,
    event_id: int,
    authorization: str | None = Header(default=None)
):
    user = require_user(authorization)

    for i, e in enumerate(PROJECT_EVENTS):
        if e["id"] == event_id and e["project_id"] == project_id:
            if e["owner"] != user:
                raise HTTPException(403, "No permission")
            PROJECT_EVENTS.pop(i)
            return {"msg": "Deleted"}

    raise HTTPException(404, "Event not found")

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