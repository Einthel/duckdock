---
name: lan7-network-collector
description: Guidelines and patterns for Lan7 network discovery, asynchronous SNMP polling, Win32 ICMP ping, FDB/ARP/LLDP ingestion, and batch SQLite writes.
---

# Lan7 Network Collector & Polling Skill

This skill governs data collection, socket management, and batch ingestion in Lan7 under PyInstaller and Windows constraints.

## 1. PyInstaller & Windows Portability
- **Pure Python or Win32 API Only**:
  - Prohibited: C-extensions that break standalone PyInstaller compilation (e.g., `uvloop`, `aiosnmp`, `libsnmp`).
  - Ping implementation: Pure Win32 `IcmpSendEcho` via `ctypes.windll.iphlpapi` with non-blocking async executor.
  - SNMP implementation: Pure Python SNMP engine (`pysnmp` / `pysnmp-lextudio`).

## 2. Network Sockets & Resilience
- **Strict Timeouts**:
  - Every UDP (SNMP) and ICMP request must have a strict timeout (1–3 seconds).
  - Always handle `asyncio.TimeoutError` and socket exceptions without interrupting the main polling cycle.
- **Worker Concurrency**:
  - Bound concurrent tasks using `asyncio.Semaphore` (e.g., 20–50 workers) to prevent socket exhaustion and OS ephemeral port starvation.

## 3. Data Normalization & Ingestion Pipeline
- **IP Addressing**:
  - IP comparisons and ordering: numeric octet parsing (`[int(x) for x in ip.split('.')]`).
- **MAC Addresses**:
  - Normalize all MACs into uppercase colon-delimited format: `AA:BB:CC:DD:EE:FF`.
  - Use `mac_to_oid_suffix` when querying Bridge/Q-Bridge MIBs via SNMP GET.
- **SQLite Batch Storage**:
  - Accumulate discovered devices, interfaces, FDB rows, and ARP entries in memory buffers.
  - Flush to SQLite using `write_gate_session()` in bulk chunks (Bulk Insert / Upsert) to avoid WAL locking and event loop stall.

