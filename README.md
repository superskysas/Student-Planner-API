# Student Planner API

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-6.0+-green.svg)](https://mongodb.com)


**Student Planner API** — это современное веб-приложение для управления студенческими задачами, построенное на FastAPI с поддержкой импорта праздников и событий из внешних источников.

## ✨ Возможности

- 🔐 **JWT-аутентификация** с безопасной авторизацией
- 📝 **Управление задачами** - создание, редактирование, удаление, поиск
- 🎉 **Импорт праздников** из Nager.Date API
- 🗄️ **MongoDB** для надежного хранения данных
- 📚 **Автоматическая Swagger документация** на `/docs`
- 🌐 **CORS поддержка** для фронтенд интеграции
- 🛡️ **Pydantic валидация** для безопасности данных
- 🎯 **RESTful API** с четкой структурой эндпоинтов

## 🚀 Быстрый старт

### Системные требования

- Python 3.11+
- MongoDB 6.0+
- pip или poetry

### Установка и запуск

1. **Клонируйте репозиторий**
   ```bash
   git clone https://github.com/yourusername/student-planner-api.git
   cd student-planner-api
   ```

2. **Создайте виртуальное окружение**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # или
   venv\Scripts\activate     # Windows
   ```

3. **Установите зависимости**
   
   С pip:
   ```bash
   pip install -r requirements.txt
   ```

4. **Настройте переменные окружения**
   ```bash
   export MONGO_DSN="mongodb://localhost:27017"
   export JWT_SECRET_KEY="your-super-secret-jwt-key"
   export JWT_ALGORITHM="HS256"
   export ACCESS_TOKEN_EXPIRE_MINUTES="60"
   ```

5. **Запустите приложение**
   ```bash
   python -m src.app.main
   ```

   Или с uvicorn для продакшена:
   ```bash
   uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Откройте документацию**
   
   Перейдите на http://localhost:8000/docs для интерактивной Swagger документации

## 📖 API Документация

### 🔑 Аутентификация

#### Регистрация
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

#### Авторизация
```http
POST /auth/jwt/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=SecurePassword123!
```

**Ответ:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### 📝 Управление задачами

#### Создать задачу
```http
POST /tasks
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "title": "Подготовиться к экзамену",
  "date": "2024-01-15",
  "type": "deadline"
}
```

#### Получить список задач
```http
GET /tasks?date=2024-01-15&type=deadline&q=экзамен
Authorization: Bearer {access_token}
```

#### Получить задачу по ID
```http
GET /tasks/{task_id}
Authorization: Bearer {access_token}
```

#### Обновить задачу
```http
PATCH /tasks/{task_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "title": "Новое название задачи",
  "status": "done"
}
```

#### Удалить задачу
```http
DELETE /tasks/{task_id}
Authorization: Bearer {access_token}
```

### 🎉 Импорт праздников

#### Импортировать праздники из Nager.Date API
```http
POST /import/nager?country=US&year=2024
Authorization: Bearer {access_token}
```

**Ответ:**
```json
{
  "imported": 12,
  "skipped": 3,
  "details": [
    {
      "id": "64a1b2c3d4e5f6789abcdef0",
      "title": "New Year's Day",
      "date": "2024-01-01",
      "type": "holiday"
    }
  ]
}
```

## 🛠️ Разработка

### Структура проекта

```
src/
├── app/
│   ├── api/           # REST API эндпоинты
│   │   ├── auth.py    # Аутентификация
│   │   ├── tasks.py   # Управление задачами
│   │   └── importers.py # Импорт внешних данных
│   ├── core/          # Основная конфигурация
│   │   ├── config.py  # Настройки приложения
│   │   ├── deps.py    # Проверка пользователя
│   │   └── security.py # JWT и безопасность
│   ├── db/            # База данных
│   │   ├── mongo.py   # Подключение к MongoDB
│   │   └── repositories.py # Репозитории данных
│   ├── models/        # Pydantic модели
│   │   ├── tasks.py   # Модели задач
│   │   └── users.py   # Модели пользователей
│   ├── services/      # Бизнес-логика
│   │   └── nager.py   # Сервис для работы с Nager API
│   └── main.py        # Точка входа приложения
```

### Переменные окружения

| Переменная | Описание | По умолчанию |
|-----------|----------|----|
| `MONGO_DSN` | URL подключения к MongoDB | `mongodb://localhost:27017` |
| `JWT_SECRET_KEY` | Секретный ключ для JWT | (обязательно) |
| `JWT_ALGORITHM` | Алгоритм JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни токена (мин) | `60` |
| `CORS_ALLOW_ORIGINS` | Разрешенные CORS origins | `*` |
| `DISABLE_MONGO_STARTUP` | Отключить MongoDB при старте | `0` |

## 🐳 Docker

### Использование Makefile

В проекте есть готовый Makefile для управления MongoDB:

```bash
# Запустить MongoDB
make up

# Проверить статус
make status

# Посмотреть логи
make logs

# Открыть mongosh
make mongosh

# Запустить mongo-express (веб-интерфейс)
make express_up

# Остановить
make stop
make express_down

# Помощь
make help
```

## 📊 Swagger документация

После запуска сервера, интерактивная API документация доступна по адресам:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc  


⭐ Поставьте звезду, если проект был полезен!
