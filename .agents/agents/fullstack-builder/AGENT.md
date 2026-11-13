name: fullstack-builder
description: "Сквозная реализация функционала: бэкенд FastAPI, схемы SQLite и клиентский интерфейс Vanilla JS"
mcp_servers:
  - serena
  - memory-bank
  - filesystem
  - sqlite
  - context7
skills:
  - fastapi-pro
  - python-pro
  - lan7-frontend-vanilla
  - sqlite-migrations
  - pydantic-contracts
tools_policy:
  scope_restrictions:
    - "Соблюдать правило Zero-NPM для фронтенда: только Vanilla JS (ES6+) и нативный CSS в lan7/web/static/"
    - "Асинхронные операции с БД выполнять строго через AsyncSession / write_gate_session"
    - "При работе с внешними библиотеками (FastAPI, SQLAlchemy 2.0, Pydantic v2, Cytoscape.js) использовать MCP-сервер context7 (resolve-library-id, query-docs) для проверки актуальных сигнатур и breaking changes"
    - "Обязательно обновлять lan7/.md/changelog.md и прогонять тесты через pytest"

