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
        # Подготавливаем данные для создания задачи
        task_data = {
            "title": payload.title,
            "date": payload.date.isoformat(),  # Конвертируем дату в строку ISO format
            "type": payload.type,
            "status": "todo",  # По умолчанию новые задачи имеют статус "todo"
            "source": "local",  # Задачи, создаваемые пользователем, имеют источник "local"
            # Локальные задачи не имеют meta.source_id, чтобы избежать конфликтов с unique index
        }
        
        # Создаем задачу в базе данных для текущего пользователя
        created_task = await tasks.create(user["id"], task_data)
        
        # Конвертируем результат в Pydantic модель TaskOut
        return TaskOut(
            id=created_task["id"],
            title=created_task["title"],
            date=created_task["date"],  # Дата уже в формате строки из репозитория
            type=created_task["type"],
            status=created_task["status"],
            source=created_task["source"]
        )
        
    except KeyError as e:
        # Если в объекте user отсутствует поле id
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user data"
        )
    except ValueError as e:
        # Ошибки валидации данных (например, неправильный тип задачи)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task data: {str(e)}"
        )
    except Exception as e:
        # Логируем неожиданные ошибки для отладки
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
        # Валидируем тип задачи, если указан
        allowed_types = {"task", "meeting", "deadline", "holiday", "news"}
        if type is not None and type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid task type. Allowed types: {', '.join(sorted(allowed_types))}"
            )
        
        # Получаем список задач из репозитория
        task_list = await tasks.list(
            user_id=user["id"],
            date_eq=date,
            type_eq=type,
            q=q
        )
        
        # Конвертируем каждую задачу в Pydantic модель TaskOut
        result = []
        for task_dict in task_list:
            task_out = TaskOut(
                id=task_dict["id"],
                title=task_dict["title"],
                date=task_dict["date"],  # Дата уже в формате строки из репозитория
                type=task_dict["type"],
                status=task_dict["status"],
                source=task_dict["source"]
            )
            result.append(task_out)
        
        return result
        
    except HTTPException:
        # Пропускаем уже созданные HTTPException
        raise
    except KeyError as e:
        # Если в объекте user отсутствует поле id
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user data"
        )
    except ValueError as e:
        # Ошибки валидации параметров
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameters: {str(e)}"
        )
    except Exception as e:
        # Логируем неожиданные ошибки для отладки
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
        # Проверяем, что task_id не пустой
        if not task_id or not task_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task ID cannot be empty"
            )
        
        # Получаем задачу из репозитория
        task_dict = await tasks.get(user["id"], task_id.strip())
        
        # Проверяем, что задача найдена
        if task_dict is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Конвертируем в Pydantic модель TaskOut
        return TaskOut(
            id=task_dict["id"],
            title=task_dict["title"],
            date=task_dict["date"],  # Дата уже в формате строки из репозитория
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
        # Проверяем, что task_id не пустой
        if not task_id or not task_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task ID cannot be empty"
            )
        
        # Проверяем, что есть данные для обновления
        update_data = patch.dict(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data provided for update"
            )
        
        # Преобразуем дату в строку, если она есть
        # Если дата None, удаляем её из update_data, чтобы не изменять существующую дату
        if "date" in update_data:
            if update_data["date"] is not None:
                update_data["date"] = update_data["date"].isoformat()
            else:
                # Удаляем date из update_data, если она None
                del update_data["date"]
        
        # Обновляем задачу в репозитории
        updated_task = await tasks.update(user["id"], task_id.strip(), update_data)
        
        # Проверяем, что задача обновлена
        if updated_task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Конвертируем в Pydantic модель TaskOut
        return TaskOut(
            id=updated_task["id"],
            title=updated_task["title"],
            date=updated_task["date"], 
            type=updated_task["type"],
            status=updated_task["status"],
            source=updated_task["source"]
        )
        
    except HTTPException:
        # Пропускаем уже созданные HTTPException
        raise
    except InvalidId:
        # Ошибка некорректного ObjectId в MongoDB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task ID format"
        )
    except KeyError as e:
        # Ошибка в структуре данных пользователя или задачи
        if str(e) == "'id'":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user data"
            )
        else:
            # Ошибка в структуре данных задачи
            print(f"Missing field in task data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error: invalid task data structure"
            )
    except Exception as e:
        # Логируем неожиданные ошибки
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
    # Удаляем задачу из репозитория
    deleted = await tasks.delete(user["id"], task_id)
    
    # Если задача не найдена или не принадлежит пользователю, возвращаем 404
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    # Если удаление прошло успешно, FastAPI автоматически вернет 204 No Content
