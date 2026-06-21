import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.routers import leaves, plans, sort

app = FastAPI(
    title="贝叶经叶片整理系统",
    description="根据穿绳孔位置、残存文字和叶片尺寸推测贝叶经原始顺序的网页应用",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "贝叶经叶片整理系统运行正常"}


app.include_router(leaves.router, prefix="/api")
app.include_router(plans.router, prefix="/api")
app.include_router(sort.router, prefix="/api")

frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
