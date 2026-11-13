---
name: pydantic-contracts
description: Паттерны валидации Pydantic v2 для топологических узлов и ребер, строгая сериализация графа в JSON, контракты API.
---

# Pydantic v2 Contracts Skill for Lan7

This skill governs data validation, model serialization, and API request/response schemas in Lan7.

## 1. Pydantic v2 Standards
- Always use Pydantic v2 syntax (`model_config = ConfigDict(...)`, `@field_validator`, `@model_validator`).
- Do **NOT** use deprecated v1 methods (`@validator`, `dict()`, `.parse_obj()`).
- Use `from_attributes = True` for SQLAlchemy ORM model conversion.
- **Context7 Protocol**: В спорных моментах синтаксиса и миграции (Pydantic v1 vs v2, кастомные сериализаторы, Annotated типы) проверять актуальную документацию через MCP `context7` (`resolve-library-id`, `query-docs`).

## 2. Network Data Validators

### 2.1. IP Address Validation
```python
from pydantic import BaseModel, field_validator
import ipaddress

class SwitchBase(BaseModel):
    ip: str

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        try:
            ipaddress.IPv4Address(v.strip())
            return v.strip()
        except ValueError:
            raise ValueError(f"Invalid IPv4 address: {v}")
```

### 2.2. MAC Normalization Validator
```python
import re

MAC_CLEAN_RE = re.compile(r'[^0-9A-Fa-f]')

class HostBase(BaseModel):
    mac: str

    @field_validator("mac")
    @classmethod
    def normalize_mac(cls, v: str) -> str:
        cleaned = MAC_CLEAN_RE.sub('', v).upper()
        if len(cleaned) != 12:
            raise ValueError(f"MAC must contain exactly 12 hex digits: {v}")
        return ':'.join(cleaned[i:i+2] for i in range(0, 12, 2))
```

## 3. Cytoscape Graph Payload Contracts
- Graph payload must be strictly serialized into:
```python
class CytoscapeNodeData(BaseModel):
    id: str
    label: str
    ip: str
    vendor: str | None = None
    model: str | None = None
    status: str = "offline"
    is_root: bool = False

class CytoscapeEdgeData(BaseModel):
    id: str
    source: str
    target: str
    source_port: str
    target_port: str
    is_manual: bool = False
    link_type: str = "LLDP"

class CytoscapePayload(BaseModel):
    nodes: list[dict[str, CytoscapeNodeData]]
    edges: list[dict[str, CytoscapeEdgeData]]
```

