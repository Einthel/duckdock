---
name: lan7-frontend-vanilla
description: Architecture, standards, and practices for the Lan7 Vanilla JS (ES6+) Single Page Application, Cytoscape.js network canvas, and native CSS styling without npm build tools.
---

# Lan7 Vanilla SPA & Cytoscape Frontend Skill

This skill enforces strict frontend conventions for Lan7 in accordance with Rule #3 (`GEMINI.md`).

## 1. Zero-NPM Architecture
- **No Node.js / NPM Build Pipeline**: Never introduce webpack, vite, babel, react, vue, or tailwind cli dependencies.
- **Pure Native Assets**: All code is served directly from `lan7/web/static/`:
  - `css/style.css` - Native CSS variables, glassmorphism, dark theme.
  - `js/app.js` and `js/index.js` - Application bootstrap and router.
  - `js/modules/` - Modular ES6 imports (`core`, `topology`, `tracker`, `ncm`, `passport`, `ui`).
  - `js/cytoscape.min.js` - Prebundled vendor library.

## 2. Cytoscape.js Topology Canvas Rules
- **Coordinate Hit-Testing & Drag-and-Drop**:
  - Keep canvas coordinate conversion precise (`cy.pan()`, `cy.zoom()`).
  - Drag threshold: exactly 6px to avoid false triggers during click selection.
  - Visual feedback: `.switch-drag-ghost` with `backdrop-filter: blur(8px)`, `.drag-over`, and `.drop-success`.
  - Manual links indicator: badge 📌 and attribute `is_manual: true`.
- **Node & Port Interaction**:
  - Click-to-Pick allows populating source and target slots without dragging.
  - Port sorting: use natural alphanumeric sort (`compareNatural`, e.g., `gi1/0/2` < `gi1/0/10`).
- **Context7 Canvas & Web API Protocol**:
  - При обращении к редким или сложным методам Cytoscape.js (layout options, animation signatures, canvas export) и нативным браузерным API сверяться с документацией через MCP `context7`.

## 3. UI/UX & Data Standards
- **Debounced Inputs**: All text search inputs, table filters, and auto-completers MUST use a 300ms debounce timer.
- **IP & MAC Presentation**:
  - IP addresses must be sorted octet-by-octet numerically, never lexicographically as strings.
  - MAC addresses displayed normalized in uppercase (`AA:BB:CC:DD:EE:FF`).
- **Security Guard Awareness**:
  - When accessed from remote IPs (`lanWeb`), mutating endpoints (`POST`, `PUT`, `DELETE`) return `403 Forbidden`.
  - The UI must handle 403 gracefully by showing an operator advisory (Local engine only / Read-only mode).

