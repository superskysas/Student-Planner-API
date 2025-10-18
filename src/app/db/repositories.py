from __future__ import annotations

import re
import uuid
from datetime import date
from typing import Any, Optional, Protocol

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

UserDict = dict[str, Any]
TaskDict = dict[str, Any]

ALLOWED_TYPES = {"task", "meeting", "deadline", "holiday", "news"}
ALLOWED_STATUS = {"todo", "done"}


class UsersRepository(Protocol):
    async def create(self, email: str, password_hash: str) -> UserDict: ...
    async def get_by_email(self, email: str) -> Optional[UserDict]: ...
    async def get_by_id(self, user_id: str) -> Optional[UserDict]: ...


class TasksRepository(Protocol):
    async def create(self, user_id: str, data: TaskDict) -> TaskDict: ...
    async def get(self, user_id: str, task_id: str) -> Optional[TaskDict]: ...
    async def list(
        self, user_id: str, *, date_eq: Optional[date] = None, type_eq: Optional[str] = None, q: Optional[str] = None
    ) -> list[TaskDict]: ...
    async def update(self, user_id: str, task_id: str, patch: dict[str, Any]) -> Optional[TaskDict]: ...
    async def delete(self, user_id: str, task_id: str) -> bool: ...
    async def insert_many_nager(self, user_id: str, items: list[TaskDict]) -> tuple[int, list[TaskDict]]: ...


class MotorUsersRepository(UsersRepository):
    def __init__(self, coll: AsyncIOMotorCollection) -> None:
        self.coll = coll

    @staticmethod
    def _to_public(doc: dict[str, Any]) -> UserDict:
        return {
            "id": str(doc["_id"]),
            "email": doc["email"],
            "password_hash": doc["password_hash"],
            "created_at": doc.get("created_at"),
        }

    async def create(self, email: str, password_hash: str) -> UserDict:
        doc = {"email": email, "password_hash": password_hash}
        res = await self.coll.insert_one(doc)
        created = await self.coll.find_one({"_id": res.inserted_id})
        assert created
        return self._to_public(created)

    async def get_by_email(self, email: str) -> Optional[UserDict]:
        doc = await self.coll.find_one({"email": email})
        return self._to_public(doc) if doc else None

    async def get_by_id(self, user_id: str) -> Optional[UserDict]:
        doc = await self.coll.find_one({"_id": ObjectId(user_id)})
        return self._to_public(doc) if doc else None


class MotorTasksRepository(TasksRepository):
    def __init__(self, coll: AsyncIOMotorCollection) -> None:
        self.coll = coll

    @staticmethod
    def _to_public(doc: dict[str, Any]) -> TaskDict:
        return {
            "id": str(doc["_id"]),
            "user_id": str(doc["user_id"]),
            "title": doc["title"],
            "date": doc["date"],
            "type": doc["type"],
            "status": doc["status"],
            "source": doc.get("source", "local"),
            "meta": doc.get("meta", {}),
        }

    async def create(self, user_id: str, data: TaskDict) -> TaskDict:
        doc = {
            "user_id": ObjectId(user_id),
            "title": data["title"],
            "date": data["date"], 
            "type": data.get("type", "task"),
            "status": data.get("status", "todo"),
            "source": data.get("source", "local"),
            "meta": data.get("meta", {}),
        }
        res = await self.coll.insert_one(doc)
        inserted = await self.coll.find_one({"_id": res.inserted_id})
        assert inserted
        return self._to_public(inserted)

    async def get(self, user_id: str, task_id: str) -> Optional[TaskDict]:
        doc = await self.coll.find_one({"_id": ObjectId(task_id), "user_id": ObjectId(user_id)})
        return self._to_public(doc) if doc else None

    async def list(
        self, user_id: str, *, date_eq: Optional[date] = None, type_eq: Optional[str] = None, q: Optional[str] = None
    ) -> list[TaskDict]:
        query: dict[str, Any] = {"user_id": ObjectId(user_id)}
        if date_eq:
            query["date"] = date_eq.isoformat()
        if type_eq:
            query["type"] = type_eq
        if q:
            query["title"] = {"$regex": re.escape(q), "$options": "i"}
        cursor = self.coll.find(query).sort("date", 1)
        docs = [self._to_public(d) async for d in cursor]
        return docs

    async def update(self, user_id: str, task_id: str, patch: dict[str, Any]) -> Optional[TaskDict]:
        res = await self.coll.find_one_and_update(
            {"_id": ObjectId(task_id), "user_id": ObjectId(user_id)},
            {"$set": patch},
            return_document=True,
        )
        return self._to_public(res) if res else None

    async def delete(self, user_id: str, task_id: str) -> bool:
        res = await self.coll.delete_one({"_id": ObjectId(task_id), "user_id": ObjectId(user_id)})
        return res.deleted_count == 1

    async def insert_many_nager(self, user_id: str, items: list[TaskDict]) -> tuple[int, list[TaskDict]]:
        """Вставляет праздники, пропуская дубли по meta.source_id для user_id."""
        if not items:
            return 0, []
        for it in items:
            it["user_id"] = ObjectId(user_id)
        inserted: list[TaskDict] = []
        for it in items:
            res = await self.coll.update_one(
                {"user_id": it["user_id"], "meta.source_id": it["meta"]["source_id"]},
                {"$setOnInsert": it},
                upsert=True,
            )
            if res.upserted_id:
                doc = await self.coll.find_one({"_id": res.upserted_id})
                if doc:
                    inserted.append(self._to_public(doc))
        return len(inserted), inserted


class InMemoryUsersRepository(UsersRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, UserDict] = {}
        self._by_email: dict[str, str] = {}

    async def create(self, email: str, password_hash: str) -> UserDict:
        if email in self._by_email:
            raise ValueError("duplicate")
        uid = uuid.uuid4().hex
        doc: UserDict = {"id": uid, "email": email, "password_hash": password_hash}
        self._by_id[uid] = doc
        self._by_email[email] = uid
        return doc

    async def get_by_email(self, email: str) -> Optional[UserDict]:
        uid = self._by_email.get(email)
        return self._by_id.get(uid) if uid else None

    async def get_by_id(self, user_id: str) -> Optional[UserDict]:
        return self._by_id.get(user_id)


class InMemoryTasksRepository(TasksRepository):
    def __init__(self) -> None:
        self._items: dict[str, TaskDict] = {}  

    async def create(self, user_id: str, data: TaskDict) -> TaskDict:
        tid = uuid.uuid4().hex
        doc = {
            "id": tid,
            "user_id": user_id,
            "title": data["title"],
            "date": data["date"],
            "type": data.get("type", "task"),
            "status": data.get("status", "todo"),
            "source": data.get("source", "local"),
            "meta": data.get("meta", {}),
        }
        self._items[tid] = doc
        return doc

    async def get(self, user_id: str, task_id: str) -> Optional[TaskDict]:
        doc = self._items.get(task_id)
        if not doc or doc["user_id"] != user_id:
            return None
        return doc

    async def list(
        self, user_id: str, *, date_eq: Optional[date] = None, type_eq: Optional[str] = None, q: Optional[str] = None
    ) -> list[TaskDict]:
        items = [d for d in self._items.values() if d["user_id"] == user_id]
        if date_eq:
            items = [d for d in items if d["date"] == date_eq.isoformat()]
        if type_eq:
            items = [d for d in items if d["type"] == type_eq]
        if q:
            items = [d for d in items if q.lower() in d["title"].lower()]
        return sorted(items, key=lambda x: x["date"])

    async def update(self, user_id: str, task_id: str, patch: dict[str, Any]) -> Optional[TaskDict]:
        doc = await self.get(user_id, task_id)
        if not doc:
            return None
        doc.update(patch)
        return doc

    async def delete(self, user_id: str, task_id: str) -> bool:
        doc = await self.get(user_id, task_id)
        if not doc:
            return False
        del self._items[task_id]
        return True

    async def insert_many_nager(self, user_id: str, items: list[TaskDict]) -> tuple[int, list[TaskDict]]:
        existing_source_ids = {
            d["meta"].get("source_id")
            for d in self._items.values()
            if d["user_id"] == user_id and d.get("meta")
        }
        inserted: list[TaskDict] = []
        for it in items:
            sid = it["meta"]["source_id"]
            if sid in existing_source_ids:
                continue
            created = await self.create(user_id, it)
            inserted.append(created)
            existing_source_ids.add(sid)
        return len(inserted), inserted
