"""
FastAPI Main Application

Smartway Analytics API 서버
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import analytics

# FastAPI 앱 생성
app = FastAPI(
    title="Smartway Analytics API",
    description="버스 노선 분석 및 시각화 API",
    version="1.0.0"
)

# CORS 설정 (Next.js와 통신)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes 등록
app.include_router(analytics.router, prefix="/api", tags=["analytics"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Smartway Analytics API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
