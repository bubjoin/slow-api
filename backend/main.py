from fastapi import FastAPI 
from datetime import datetime
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9)) # UTC에 9시간 더하는 방식으로 서버 로그 기준으로 권장하지 않음

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS 설정 (Day 0 기본값), 개발단계
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Day 0: 모두 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MEMOS = []

@app.post("/memo")
def create_memo(text: str):
    memo = {
        "text": text,
        "created_at": datetime.now(KST).isoformat()
        # datetime.utcnow().isoformat()
    }
    MEMOS.append(memo)
    return memo

@app.get("/memo")
def list_memos():
    return MEMOS

