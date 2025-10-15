# ctdmate/ui/api.py
from __future__ import annotations

# 단일 ASGI 앱 재노출. 필요 시 CORS 등 미들웨어만 추가.
from fastapi import FastAPI
try:
    from ctdmate.app.router import app as _core_app
except Exception:
    from ..app.router import app as _core_app  # type: ignore

app: FastAPI = _core_app

# 선택: CORS
try:
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
except Exception:
    pass

# 로컬 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ctdmate.ui.api:app", host="0.0.0.0", port=8000, reload=False)
