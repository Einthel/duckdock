---
name: test-driven-development
description: Шаблоны фикстур Pytest для асинхронных роутов FastAPI, тестирование сетевых структур, изоляция SQLite БД и регрессионный анализ.
---

# Test-Driven Development (TDD) Skill for Lan7

This skill governs testing conventions, async test clients, SQLite in-memory isolation, and mock patterns for Lan7.

## 1. Test Environment Rules
- **Python Environment**: Always run tests using the active virtual environment:
  ```powershell
  & ".\lan7\.venv\Scripts\pytest.exe" lan7/tests/test_lanweb_v2.py
  ```
- **Context7 Testing Protocol**: При настройке сложных асинхронных фикстур (`pytest-asyncio`), моков или параметров ASGI-клиентов `httpx` сверяться с актуальной документацией через MCP `context7`.
- **Async Engine Isolation**:
  - Use `aiosqlite` with in-memory SQLite (`sqlite+aiosqlite:///:memory:`) for fast unit tests.
  - Or use temporary files with immediate teardown.

## 2. FastAPI Async TestClient Pattern
```python
import pytest
from httpx import AsyncClient, ASGITransport
from lan7.web.server import app

@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        yield client
```

## 3. Network Mocking Patterns
- **SNMP Engine Mock**:
  Never attempt real socket calls in unit tests. Mock `SNMPCollector.query_oid` and `pysnmp` responses with deterministic bytes/integers.
- **Win32 Ping Mock**:
  Mock `win32_ping` / `ctypes.windll.iphlpapi` to return simulated RTT and packet success.

## 4. Regression & Migration Checks
- Always verify that schema updates don't break existing databases without new migrations.
- Verify that SecurityGuardMiddleware strictly returns `403` for remote non-loopback IP requests attempting mutating methods (`POST`, `PUT`, `DELETE`).

## 5. Test Taxonomy & Marker Standards
- **Automatic Test Discovery**: `testpaths = lan7/tests`, `python_files = test_*.py`. Individual tests do not need manual registration.
- **Markers Registry (in `pytest.ini`)**:
  - `@pytest.mark.core`: Fast pure unit tests (no I/O, no SQLite, no sockets) in `lan7/tests/unit/`. Target execution time: `< 1.5s` for all core tests (`pytest -m core`).
  - `@pytest.mark.integration`: Database, FastAPI routes, background workers, and SSH NCM engine tests.
  - `@pytest.mark.ui_contract`: Frontend static contracts (HTML/CSS cascade order, cache busting `?v=`, JS module exports, Node.js DOM-tests).
  - Any new marker MUST be registered in `pytest.ini` and `lan7/pyproject.toml` under `markers` before use to prevent `PytestUnknownMarkWarning`.
- **Zero Warnings Enforcement**: The test report must always be clean (`0 warnings`). Filter deprecations from external libraries in `pytest.ini`.

## 6. Idling & Timeout Zero-Tolerance
- Never leave active `setTimeout` / `setInterval` in Node.js DOM tests (`test_*.mjs`). Call cleanup helpers like `Lan7Toast.clearAll()` or component `destroy()`.
- Never perform real socket pings with timeouts against unreachable IPs in tests. Use `AsyncMock` or `patch` to simulate fast responses without idling.


