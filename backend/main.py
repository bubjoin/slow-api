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
MEMOS = []      # {text, created_at, owner}
EVENTS = []   # 일정 저장소

memo_id_seq = itertools.count(1)
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

# ===== 일정 삭제 (로그인 필수) =====
@app.delete("/events/{event_id}")
def delete_event(
    event_id: int,
    authorization: str | None = Header(default=None)
):
    user = require_user(authorization)

    for i, e in enumerate(EVENTS):
        if e["id"] == event_id:
            if e["owner"] != user:
                raise HTTPException(status_code=403, detail="No permission")
            EVENTS.pop(i)
            return {"msg": "Deleted"}

    raise HTTPException(status_code=404, detail="Event not found")

# ===== 일정 수정 (로그인 필수) =====
@app.put("/events/{event_id}")
def update_event(
    event_id: int,
    title: str,
    date: str,
    authorization: str | None = Header(default=None)
):
    user = require_user(authorization)

    for e in EVENTS:
        if e["id"] == event_id:
            if e["owner"] != user:
                raise HTTPException(status_code=403, detail="No permission")
            e["title"] = title
            e["date"] = date
            return e

    raise HTTPException(status_code=404, detail="Event not found")

# ===== 일정 생성 (로그인 필수) =====
@app.post("/events")
def create_event(
    title: str,
    date: str,   # YYYY-MM-DD
    authorization: str | None = Header(default=None)
):
    user = require_user(authorization)

    event = {
        "id": next(event_id_seq),
        "title": title,
        "date": date,
        "owner": user
    }
    EVENTS.append(event)
    return event

# ===== 일정 조회 (로그인 필수) =====
@app.get("/events")
def list_events(
    authorization: str | None = Header(default=None)
):
    user = require_user(authorization)
    return [e for e in EVENTS if e["owner"] == user]

# ===== 메모 삭제 (로그인 필수) =====
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

# ===== 메모 수정 (로그인 필수) =====
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

# ===== 메모 작성 (로그인 필수) =====
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

# ===== 내 메모 조회 (로그인 필수) =====
@app.get("/memo")
def list_memos(authorization: str | None = Header(default=None)):
    user = require_user(authorization)
    return [m for m in MEMOS if m["owner"] == user]
