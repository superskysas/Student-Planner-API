from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.app.core.config import settings
from src.app.db.repositories import (
    MotorTasksRepository,
    MotorUsersRepository,
    TasksRepository,
    UsersRepository,
)

MONGO_CLIENT_KEY = "mongo_client"
MONGO_DB_KEY = "mongo_db"


async def init_mongo(app: FastAPI) -> None:
    """Создаёт Mongo client и индексы (если их ещё нет)."""
    print("MONGO_DSN", settings.MONGO_DSN)
    client = AsyncIOMotorClient(settings.MONGO_DSN)
    db = client[settings.MONGO_DB]
    app.state.__setattr__(MONGO_CLIENT_KEY, client)
    app.state.__setattr__(MONGO_DB_KEY, db)

    # Индексы
    await db["users"].create_index("email", unique=True)
    await db["tasks"].create_index([("user_id", 1), ("date", 1)])
    await db["tasks"].create_index([("user_id", 1), ("type", 1)])
    await db["tasks"].create_index([("user_id", 1), ("meta.source_id", 1)], unique=True, sparse=True)


async def close_mongo(app: FastAPI) -> None:
    client: Optional[AsyncIOMotorClient] = getattr(app.state, MONGO_CLIENT_KEY, None)
    if client:
        client.close()


def _get_db_from_app() -> AsyncIOMotorDatabase:
    from src.app.main import app 
    db = getattr(app.state, MONGO_DB_KEY, None)
    if db is None:
        client = AsyncIOMotorClient(settings.MONGO_DSN)
        db = client[settings.MONGO_DB]
        app.state.__setattr__(MONGO_DB_KEY, db)
    return db

async def get_users_repo() -> UsersRepository:
    db = _get_db_from_app()
    return MotorUsersRepository(db["users"])


async def get_tasks_repo() -> TasksRepository:
    db = _get_db_from_app()
    return MotorTasksRepository(db["tasks"])
