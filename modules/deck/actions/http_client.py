"""
Модуль асинхронных сетевых HTTP REST запросов (HTTP Client).
Использует стандартную библиотеку urllib.request с таймаутом 1.5с
для интеграции с локальным софтом (OpenRGB, Home Assistant, OBS REST).
"""
import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("duckdock.deck.http")


def execute_http_request(
    url: str,
    method: str = "POST",
    headers: Optional[Dict[str, str]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout_sec: float = 1.5,
) -> Tuple[bool, int, str]:
    """
    Выполняет HTTP-запрос через urllib.request с коротким таймаутом.
    Возвращает кортеж (success: bool, status_code: int, message_or_response: str).
    Гарантирует отсутствие необработанных исключений и зависаний.
    """
    if not url or not url.strip():
        return False, 0, "Указан пустой URL запроса"

    req_url = url.strip()
    req_method = method.upper()

    req_headers = {
        "User-Agent": "DuckDock-ActionPanel/1.0",
    }
    if headers:
        req_headers.update(headers)

    data: Optional[bytes] = None
    if json_body is not None:
        try:
            data = json.dumps(json_body).encode("utf-8")
            if "Content-Type" not in req_headers:
                req_headers["Content-Type"] = "application/json"
        except Exception as json_err:
            logger.error(f"Ошибка сериализации json_body: {json_err}")
            return False, 0, f"Ошибка JSON: {json_err}"

    try:
        req = urllib.request.Request(
            url=req_url,
            data=data,
            headers=req_headers,
            method=req_method,
        )

        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            status = resp.status
            raw_body = resp.read()
            body_text = raw_body.decode("utf-8", errors="replace")
            logger.info(f"HTTP {req_method} '{req_url}' завершен со статусом {status}")
            return (200 <= status < 300), status, body_text

    except urllib.error.HTTPError as http_err:
        status = http_err.code
        err_msg = http_err.read().decode("utf-8", errors="replace") if hasattr(http_err, "read") else str(http_err)
        logger.warning(f"HTTP ошибка {status} при обращении к '{req_url}': {err_msg}")
        return False, status, f"HTTP {status}: {err_msg[:200]}"

    except (urllib.error.URLError, TimeoutError) as net_err:
        logger.warning(f"Сетевая ошибка/таймаут при обращении к '{req_url}': {net_err}")
        return False, 0, f"Сетевая ошибка: {net_err}"

    except Exception as e:
        logger.error(f"Непредвиденная ошибка HTTP запроса к '{req_url}': {e}")
        return False, 0, f"Ошибка запроса: {e}"


__all__ = ["execute_http_request"]
