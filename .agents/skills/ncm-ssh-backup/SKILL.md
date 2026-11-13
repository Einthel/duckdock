---
name: ncm-ssh-backup
description: Standards and guidelines for the Lan7 Network Configuration Management (NCM) module, SSH backup drivers, config normalization, and SHA-256 deduplication.
---

# Lan7 NCM (Network Configuration Management) Skill

This skill guides the implementation and extension of the NCM backup system in Lan7.

## 1. Storage & Deduplication Architecture
- All configurations are saved to: `data/backups/{switch_ip_or_hostname}/{switch_name}_{YYYY-MM-DD_HH-mm-ss}.cfg`.
- **Normalization Pipeline**: Before hashing or storing, strip dynamic lines:
  - Uptime, timestamp banners, clock markers.
  - NTP clock-period markers (e.g., `ntp clock-period <num>`).
  - Cryptographic ephemeral secrets or dynamic session tokens if present.
- **Deduplication Check**:
  - Compute `SHA-256` of the normalized config text.
  - If identical to the switch's `last_backup_hash`: do **NOT** write a new file to disk.
  - Set status to `NO_CHANGE` and update `last_backup_check`.
  - If changed: save new `.cfg` file, record revision in `switch_backups` table, emit `AlertLog` event.

## 2. Vendor Drivers Architecture
- Support core CLI dialects:
  - `eltex`: `terminal datadump`, `show running-config`
  - `cisco_ios`: `terminal length 0`, `show running-config`
  - `snr`: `terminal length 0`, `show running-config`
  - `huawei`: `screen-length 0 temporary`, `display current-configuration`
  - `mikrotik`: `/export verbose`
  - `generic`: generic fallback
- Always ensure SSH connection uses strict timeout (2-5s connect timeout, 10s command execution timeout).
- Catch authentication failures and mark `last_backup_status = "AUTH_FAILED"`.

## 3. Database Models Reference
- `NCMCredential`: stores encrypted/salted credentials, auth type (`password` / `ssh_key`), optional enable password.
- `Switch` extension fields: `ncm_enabled`, `ncm_driver`, `credential_id`, `last_backup_at`, `last_backup_status`, `last_backup_hash`, `last_backup_message`.
- `SwitchBackup`: `switch_id`, `created_at`, `file_path`, `sha256_hash`, `size_bytes`, `backup_type` (`SCHEDULED` / `MANUAL`), `is_baseline`, `comment`.
