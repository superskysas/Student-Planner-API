from __future__ import annotations

from datetime import date as date_cls
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.app.core.deps import get_current_user
from src.app.db.mongo import get_tasks_repo
from src.app.db.repositories import TaskDict, TasksRepository
from src.app.models.tasks import TaskCreate, TaskOut, TaskUpdate
from bson.errors import InvalidId

router = APIRouter()


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    tasks: TasksRepository = Depends(get_tasks_repo),
    user=Depends(get_current_user),
) -> TaskOut:
    """
    Создает новую задачу для текущего пользователя.
    
    Args:
        payload: Данные для создания задачи (title, date, type)
        tasks: Репозиторий задач
        user: Текущий аутентифицированный пользователь
        
    Returns:
        TaskOut: Созданная задача
        
    Raises:
        HTTPException 401: Пользователь не аутентифицирован
        HTTPException 422: Ошибка валидации данных (автоматически)
        HTTPException 500: Внутренняя ошибка сервера
    """
    try:
        task_data = {
            "title": payload.title,
            "date": payload.date.isoformat(),
            "type": payload.type,
            "status": "todo",
            "source": "local",
        }
        
        created_task = await tasks.create(user["id"], task_data)
        
        return TaskOut(
            id=created_task["id"],
            title=created_task["title"],
            date=created_task["date"],
            type=created_task["type"],
            status=created_task["status"],
            source=created_task["source"]
        )
        
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user data"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task data: {str(e)}"
        )
    except Exception as e:
        print(f"Unexpected error during task creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("", response_model=list[TaskOut])
async def list_tasks(
    tasks: TasksRepository = Depends(get_tasks_repo),
    user=Depends(get_current_user),
    date: Optional[date_cls] = Query(default=None, description="Фильтр по дате (YYYY-MM-DD)"),
    type: Optional[str] = Query(default=None, description="Фильтр по типу задачи"),
    q: Optional[str] = Query(default=None, description="Поиск по названию задачи"),
) -> list[TaskOut]:
    """
    Получает список задач текущего пользователя с возможностью фильтрации.
    
    Args:
        tasks: Репозиторий задач
        user: Текущий аутентифицированный пользователь
        date: Фильтр по дате (опционально)
        type: Фильтр по типу задачи (опционально)
        q: Поиск по названию задачи (опционально)
        
    Returns:
        list[TaskOut]: Список задач пользователя
        
    Raises:
        HTTPException 401: Пользователь не аутентифицирован
        HTTPException 400: Некорректные параметры фильтрации
        HTTPException 500: Внутренняя ошибка сервера
    """
    try:
        allowed_types = {"task", "meeting", "deadline", "holiday", "news"}
        if type is not None and type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid task type. Allowed types: {', '.join(sorted(allowed_types))}"
            )
        
        task_list = await tasks.list(
            user_id=user["id"],
            date_eq=date,
            type_eq=type,
            q=q
        )
        
        result = []
        for task_dict in task_list:
            task_out = TaskOut(
                id=task_dict["id"],
                title=task_dict["title"],
                date=task_dict["date"],
                type=task_dict["type"],
                status=task_dict["status"],
                source=task_dict["source"]
            )
            result.append(task_out)
        
        return result
        
    except HTTPException:
        raise
    except KeyError as e:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user data"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameters: {str(e)}"
        )
    except Exception as e:
        print(f"Unexpected error during task listing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: str,
    tasks: TasksRepository = Depends(get_tasks_repo),
    user=Depends(get_current_user)
) -> TaskOut:
    """
    Получает конкретную задачу по ID для текущего пользователя.
    
    Args:
        task_id: ID задачи для поиска
        tasks: Репозиторий задач
        user: Текущий аутентифицированный пользователь
        
    Returns:
        TaskOut: Данные задачи
        
    Raises:
        HTTPException 400: Некорректный ID задачи
        HTTPException 401: Пользователь не аутентифицирован
        HTTPException 404: Задача не найдена или не принадлежит пользователю
        HTTPException 500: Внутренняя ошибка сервера
    """
    try:
        if not task_id or not task_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task ID cannot be empty"
            )
        
        task_dict = await tasks.get(user["id"], task_id.strip())
        
        if task_dict is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        return TaskOut(
            id=task_dict["id"],
            title=task_dict["title"],
            date=task_dict["date"],
            type=task_dict["type"],
            status=task_dict["status"],
            source=task_dict["source"]
        )
        

    except Exception as e:
        raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )



@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: str,
    patch: TaskUpdate,
    tasks: TasksRepository = Depends(get_tasks_repo),
    user=Depends(get_current_user),
) -> TaskOut:
    """
    Обновляет данные задачи по ID для текущего пользователя.
    
    Args:
        task_id: ID задачи для обновления
        patch: Данные для обновления (могут быть частичными)
        tasks: Репозиторий задач
        user: Текущий аутентифицированный пользователь
        
    Returns:
        TaskOut: Обновленная задача
        
    Raises:
        HTTPException 400: Некорректный ID задачи или данные
        HTTPException 401: Пользователь не аутентифицирован
        HTTPException 404: Задача не найдена или не принадлежит пользователю
        HTTPException 422: Ошибка валидации данных
        HTTPException 500: Внутренняя ошибка сервера
    """
    try:
        if not task_id or not task_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task ID cannot be empty"
            )
        
        update_data = patch.dict(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data provided for update"
            )
        
        if "date" in update_data:
            if update_data["date"] is not None:
                update_data["date"] = update_data["date"].isoformat()
            else:
                del update_data["date"]
        

        updated_task = await tasks.update(user["id"], task_id.strip(), update_data)
        
        if updated_task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        return TaskOut(
            id=updated_task["id"],
            title=updated_task["title"],
            date=updated_task["date"], 
            type=updated_task["type"],
            status=updated_task["status"],
            source=updated_task["source"]
        )
        
    except HTTPException:
        raise
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task ID format"
        )
    except KeyError as e:
        if str(e) == "'id'":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user data"
            )
        else:
            print(f"Missing field in task data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error: invalid task data structure"
            )
    except Exception as e:
        print(f"Unexpected error during task update: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str, 
    tasks: TasksRepository = Depends(get_tasks_repo), 
    user=Depends(get_current_user)
):
    """
    Удаляет задачу по ID для текущего пользователя.
    
    Args:
        task_id: ID задачи для удаления
        tasks: Репозиторий задач
        user: Текущий аутентифицированный пользователь (проверка авторизации)
        
    Returns:
        204 No Content: Задача успешно удалена
        404 Not Found: Задача не найдена или не принадлежит пользователю
    """
    deleted = await tasks.delete(user["id"], task_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
