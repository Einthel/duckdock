name: bug-hunter
description: "Диагностика первопричин багов, поиск регрессий, анализ транзакций SQLite и edge cases"
mcp_servers:
  - serena
  - sequential-thinking
  - filesystem
  - sqlite
  - context7
skills:
  - ast-grep
  - python-pro
  - sqlite-migrations
  - test-driven-development
tools_policy:
  scope_restrictions:
    - "Разрешено локализовать дефекты, готовить дифференциальные патчи и писать регрессионные тесты"
    - "При нетипичных ошибках и проверке сигнатур фреймворков (FastAPI, SQLAlchemy, Pytest) использовать MCP-сервер context7"
    - "Обязательна проверка тестами через lan7/.venv/Scripts/pytest.exe перед фиксацией изменений"

