---
name: ui-form-controls
description: Шаблоны верстки инпутов для IP-адресов, масок CIDR, MAC-адресов, номеров VLAN, валидация полей на лету, индикация ошибок.
---

# UI Form Controls Skill for Lan7

This skill provides patterns and reusable code templates for network-specific inputs in Lan7 without third-party libraries.

## 1. Network Field Specifications

### 1.1. IP Address & CIDR
- **Octet Validation**: Each octet must be between `0` and `255`.
- **Octet Sorting**: All IP lists must sort by numeric octet values (`10.0.0.2` < `10.0.0.10`), not alphabetical.
- **CIDR Prefix**: Numeric range `/1` to `/32`.
- **Validation Regex**: `^(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?:\/(?:[1-9]|[12][0-9]|3[0-2]))?$`

### 1.2. MAC Address Formatter
- Accept user input in any common format:
  - `00:11:22:33:44:55`
  - `00-11-22-33-44-55`
  - `0011.2233.4455`
  - `001122334455`
- Normalize automatically on `input` or `blur` to uppercase colon format: `AA:BB:CC:DD:EE:FF`.
- Instant feedback: Show green accent border on valid 6-byte MAC, red on invalid length/hex.

### 1.3. VLAN ID & Ranges
- Range: `1` to `4094`.
- Support comma lists and ranges: `1, 10-20, 100, 200-250`.

## 2. Real-Time UX & Debouncing
- **Search & Filter Inputs**: Always attach a `300ms` debounce timer:
```javascript
function debounce(fn, delay = 300) {
  let timer = null;
  return function(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}
```
- **Error Indicators**:
  - Class `.is-invalid` with message `.form-error-msg` in CSS.
  - Native CSS `:user-invalid` styling with high contrast.

