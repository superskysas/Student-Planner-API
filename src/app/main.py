from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

from src.app.api.auth import router as auth_router
from src.app.api.importers import router as import_router
from src.app.api.tasks import router as tasks_router
from src.app.core.config import settings
from src.app.db.mongo import close_mongo, init_mongo

app = FastAPI(
    title="Student Planner API",
    version="0.2.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
app.include_router(import_router, prefix="/import", tags=["import"])

templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@app.get("/ui/tasks", response_class=HTMLResponse, tags=["ui"])
async def ui_tasks():
    html = """<!doctype html><html lang="ru"><head>
      <meta charset="utf-8" />
      <title>Мои задачи — Студенческий планировщик</title>
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <style>body{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;margin:2rem}
      table{border-collapse:collapse} td,th{border:1px solid #ddd;padding:.5rem}</style>
    </head><body>
      <h1>Мои задачи</h1>
      <p>Откройте DevTools и выполните авторизацию через API, затем <code>GET /tasks</code>.</p>
    </body></html>"""
    return HTMLResponse(html)


@app.on_event("startup")
async def on_startup() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    if os.getenv("DISABLE_MONGO_STARTUP") == "1":
        logging.getLogger(__name__).info("MongoDB initialization disabled")
        return
        
    await init_mongo(app)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    if os.getenv("DISABLE_MONGO_STARTUP") == "1":
        return
    await close_mongo(app)
