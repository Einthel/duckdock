---
name: modal-and-dialogs
description: Паттерны модальных окон, сайдбаров (drawers), закрытие по Esc и оверлею, backdrop blur, блокировка скролла фона.
---

# Modal & Dialogs Skill for Lan7

This skill enforces modal dialog and drawer (M3 Side Sheet) architectures using pure Vanilla JS and native CSS.

## 1. M3 Side Sheet / Drawer Architecture
- **Desktop (>= 1400px)**:
  - Width: `560px` fixed.
  - Push-to-Dock: Does not darken canvas with scrim on wide displays, enabling simultaneous view and graph navigation.
- **Laptop / Mobile (< 1400px)**:
  - Slide-in from right/left with translucent dark scrim backdrop (`backdrop-filter: blur(8px)`).
  - Tap/click outside on scrim triggers close.

## 2. Keyboard & Accessibility Protocols
- **Escape Key Listener**:
  - Global `keyup` event listener must close the topmost active dialog/drawer.
  - Remove listener or check active stack depth on teardown.
- **Scroll Locking**:
  - Add `overflow: hidden` to `document.body` while modal is active.
  - Remove class on dialog close to restore scroll position.

## 3. Native Animation Standards
- Use GPU-accelerated transforms:
```css
.drawer {
  position: fixed;
  top: 0;
  right: -580px;
  width: 560px;
  height: 100vh;
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  will-change: transform;
}
.drawer.open {
  transform: translateX(-580px);
}
```
- Backdrop overlay: `.modal-backdrop` with `opacity` fade.

