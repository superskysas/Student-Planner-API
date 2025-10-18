from __future__ import annotations
from typing import Annotated, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
import httpx

from src.app.core.deps import get_current_user
from src.app.db.mongo import get_tasks_repo
from src.app.db.repositories import TaskDict, TasksRepository
from src.app.services.nager import fetch_nager_public_holidays, normalize_nager_item

router = APIRouter()


@router.post("/nager", status_code=status.HTTP_200_OK)
async def import_nager(
    country: Annotated[str, Query(min_length=2, max_length=2, description="ISO-2 код страны")],
    year: Annotated[int, Query(ge=1900, le=2100, description="Год для импорта праздников")],
    tasks: TasksRepository = Depends(get_tasks_repo),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Импорт праздников из Nager.Date API.
    
    Получает праздники для указанной страны и года,
    автоматически обрабатывает дедупликацию по (user_id, meta.source_id).
    
    Args:
        country: ISO-2 код страны (например, RO, US, DE)
        year: Год для импорта (1900-2100)
        tasks: Репозиторий задач
        user: Текущий авторизованный пользователь
        
    Returns:
        Dict[str, Any]: Информация о количестве импортированных и пропущенных праздников
        
    Raises:
        HTTPException 400: Ошибки валидации параметров
        HTTPException 401: Пользователь не авторизован
        HTTPException 502: Внешний сервис недоступен
    """
    try:
        holidays_data = await fetch_nager_public_holidays(year, country)
        
        if not holidays_data:
            return {
                "imported": 0,
                "skipped": 0,
                "details": []
            }
        
        normalized_tasks = [
            normalize_nager_item(holiday, country) 
            for holiday in holidays_data
        ]
        
        imported_count, inserted_tasks = await tasks.insert_many_nager(
            user["id"], 
            [TaskDict(task) for task in normalized_tasks]
        )
        
        details: List[Dict[str, Any]] = [
            {
                "id": task["id"],
                "title": task["title"],
                "date": task["date"],
                "type": task["type"]
            }
            for task in inserted_tasks
        ]
        
        return {
            "imported": imported_count,
            "skipped": len(holidays_data) - imported_count,
            "details": details
        }
        

    except HTTPException:
            raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail="Nager.Date unavailable") from exc
