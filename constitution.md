
## Принципы разработки
1. **Clean Architecture** - четкое разделение слоев
2. **REST + WebSocket** - REST API + real-time
3.  **TDD (Test-Driven Development)** — разработка через тестирование:
    - _Red_: Написание провального теста перед кодом.
    - _Green_: Написание минимально необходимого кода для прохождения теста.
    - _Refactor_: Улучшение кода при сохранении работоспособности тестов.
4. **Database First** - схема БД определяет API

## Технологический стек

Клиент:
├── React 18 + TypeScript
├── Vite
├── Tailwind CSS
├── React Query
├── Zustand
└── React Hook Form

### Сервер (Python):

├── **Python 3.12+**  
├── **FastAPI** 
├── **SQLAlchemy 2.0** 
├── **Alembic** 
├── **PostgreSQL 16**  
├── **PyJWT + Passlib** (bcrypt)  
└── **FastAPI WebSockets** / **Socket.io (python-socketio)**


Инфраструктура:
├── Docker
├── Docker Compose
├── Nginx
└── GitHub Actions CI/CD


## Coding Standards
- ESLint + Prettier для клиента
- Ruff для линтинга Python
- Commitizen для conventional commits
- 100% тест покрытие критичных путей
- API документация OpenAPI 3.0
