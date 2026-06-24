from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes import router
from backend.app.core.config import get_settings
from backend.app.db.store import init_db


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="GenAI-based preventive health risk, lifestyle, and care guidance platform MVP.",
)

app.include_router(router, prefix="/api")
init_db()

frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
def index():
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "HealthGuard AI API is running", "docs": "/docs"}
