from __future__ import annotations
import asyncio

from fastapi import APIRouter, Depends, HTTPException, status, Form
from typing import Annotated
from pydantic import EmailStr
from pydantic import BaseModel, EmailStr

from src.app.core.config import settings
from src.app.core.security import create_access_token, hash_password, verify_password
from src.app.db.mongo import get_users_repo
from src.app.db.repositories import UsersRepository
from src.app.models.users import TokenResponse, UserCreate, UserOut, UserLogin
from passlib.context import CryptContext

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, users: UsersRepository = Depends(get_users_repo)) -> UserOut:
    """
    Регистрирует нового пользователя в системе.
    
    Args:
        user: Данные для создания пользователя (email, password)
        users: Репозиторий пользователей
        
    Returns:
        UserOut: Информация о созданном пользователе (id, email)
        
    Raises:
        HTTPException 400: Невалидные данные (некорректный email)
        HTTPException 409: Email уже зарегистрирован
        HTTPException 422: Ошибка валидации Pydantic (автоматически)
    """
    existing_user = await users.get_by_email(user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    try:
        password_hash = await asyncio.to_thread(hash_password, user.password)
        created_user = await users.create(user.email, password_hash)
        return UserOut(
            id=created_user["id"],
            email=created_user["email"]
        )
        
    except ValueError as e:
        error_msg = str(e).lower()
        if "duplicate" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        print(f"ValueError during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        print(f"Unexpected error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/jwt/login", response_model=TokenResponse)
async def login(
    username: Annotated[EmailStr, Form(..., description="Email пользователя")],
    password: Annotated[str, Form(..., min_length=1, description="Пароль пользователя")],
    users: UsersRepository = Depends(get_users_repo)
) -> TokenResponse:
    """
    Аутентификация пользователя через application/x-www-form-urlencoded.
    
    Принимает данные в формате: username=email@example.com&password=password
    
    Args:
        username: Email пользователя
        password: Пароль пользователя
        users: Репозиторий пользователей
        
    Returns:
        TokenResponse: JWT токен и информация о нём
        
    Raises:
        HTTPException 401: Неверные учетные данные
        HTTPException 422: Ошибка валидации form-data
    """
    try:
        try:
            user_login = UserLogin(username=username, password=password)
            validated_username = user_login.username
            validated_password = user_login.password
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Validation error: {str(e)}"
            )
        
        db_user = await users.get_by_email(validated_username)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        is_valid = await asyncio.to_thread(verify_password, validated_password, db_user["password_hash"])
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="LOGIN_BAD_CREDENTIALS",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = create_access_token(sub=db_user["id"])
        
        token_response = TokenResponse(
            access_token=access_token,
            token_type="bearer"
        )
        
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


