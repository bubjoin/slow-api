from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import secrets

app = FastAPI()

# CORS (개발용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 임시 저장소 (나중에 DB로 교체) =====
USERS = {}      # username -> password
TOKENS = {}     # token -> username
MEMOS = []      # {text, created_at, owner}

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

# ===== 메모 작성 (로그인 필수) =====
@app.post("/memo")
def create_memo(text: str, authorization: str | None = Header(default=None)):
    user = require_user(authorization)
    memo = {
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
