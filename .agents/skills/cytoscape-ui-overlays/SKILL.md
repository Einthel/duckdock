---
name: cytoscape-ui-overlays
description: Размещение плавающих тулбаров, контекстных меню и миникарт поверх канваса Cytoscape.js без конфликта событий мыши.
---

# Cytoscape UI Overlays Skill for Lan7

This skill ensures zero pointer-event collisions between floating HUD widgets and the Cytoscape.js canvas graph.

## 1. Z-Index Stacking Architecture
- `canvas` (Cytoscape core): `z-index: 1`
- `cytoscape-canvas-overlay` (grid, background labels): `z-index: 2`
- `floating-hud` (zoom controls, minimap, top search bar): `z-index: 10`
- `context-menu` (right-click popover on node/edge): `z-index: 50`
- `drawer` / `modal` (device passport, link creation wizard): `z-index: 100`

## 2. Event Propagation Isolation
- **Prevent Canvas Pan/Zoom on UI Click**:
  Any floating container above Cytoscape must stop mouse and pointer propagation:
```javascript
function isolateOverlayEvents(element) {
  ['mousedown', 'mousemove', 'mouseup', 'wheel', 'touchstart', 'touchend', 'click', 'dblclick'].forEach(evt => {
    element.addEventListener(evt, (e) => e.stopPropagation());
  });
}
```
- Floating overlays must specify `pointer-events: auto`, while their outer transparent wrapper uses `pointer-events: none`.

## 3. Context Menus on Canvas Elements
- Right-click (`cxttap` in Cytoscape) on nodes/edges:
  - Convert model position `node.renderedPosition()` to viewport coordinates.
  - Position overlay popup with safe boundary padding (prevent overflow off-screen).
  - Dismiss automatically on canvas tap (`tap` event on `cy`).

## 4. Drag & Drop Coexistence
- Canvas selection vs. Drag:
  - Maintain a strict `6px` drag threshold before initiating drag & drop.
  - Drag ghost element: `.switch-drag-ghost` with `backdrop-filter: blur(8px)` and `z-index: 1000`.

