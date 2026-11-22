"""
Команды истории отмены и повтора (QUndoCommand) для DuckDeck Editor.
Реализует атомарные операции:
  - AssignActionCommand: назначение действия из библиотеки на слот.
  - ClearSlotCommand: очистка слота кнопкой корзины или Del.
  - SwapButtonsCommand: обмен или копирование кнопок при Drag-and-Drop.
  - UpdatePropertyCommand: изменение отдельного свойства кнопки.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from PySide6.QtGui import QUndoCommand

from modules.deck.editor.dto import ButtonSlotDTO

if TYPE_CHECKING:
    from modules.deck.editor.window import DeckEditorWindow


class AssignActionCommand(QUndoCommand):
    """Назначение действия на слот холста."""

    def __init__(
        self,
        window: DeckEditorWindow,
        slot_index: int,
        new_dto: ButtonSlotDTO,
        old_dto: Optional[ButtonSlotDTO] = None,
        text: str = "Assign Action",
    ) -> None:
        super().__init__(text)
        self.window = window
        self.slot_index = slot_index
        self.new_dto = (
            new_dto.model_copy(deep=True)
            if hasattr(new_dto, "model_copy")
            else ButtonSlotDTO(**new_dto.__dict__)
        )
        if old_dto is not None:
            self.old_dto = (
                old_dto.model_copy(deep=True)
                if hasattr(old_dto, "model_copy")
                else ButtonSlotDTO(**old_dto.__dict__)
            )
        else:
            curr = window.get_slot_dto(slot_index)
            self.old_dto = (
                curr.model_copy(deep=True)
                if curr
                else ButtonSlotDTO(slot_index=slot_index)
            )

    def redo(self) -> None:
        self.window.apply_slot_dto(self.slot_index, self.new_dto)

    def undo(self) -> None:
        self.window.apply_slot_dto(self.slot_index, self.old_dto)


class ClearSlotCommand(QUndoCommand):
    """Очистка слота холста."""

    def __init__(
        self,
        window: DeckEditorWindow,
        slot_index: int,
        old_dto: Optional[ButtonSlotDTO] = None,
        text: str = "Clear Slot",
    ) -> None:
        super().__init__(text)
        self.window = window
        self.slot_index = slot_index
        if old_dto is not None:
            self.old_dto = (
                old_dto.model_copy(deep=True)
                if hasattr(old_dto, "model_copy")
                else ButtonSlotDTO(**old_dto.__dict__)
            )
        else:
            curr = window.get_slot_dto(slot_index)
            self.old_dto = (
                curr.model_copy(deep=True)
                if curr
                else ButtonSlotDTO(slot_index=slot_index)
            )
        self.empty_dto = ButtonSlotDTO(
            slot_index=slot_index,
            title="",
            icon="",
            category="",
            action_type="",
            hotkey="",
        )

    def redo(self) -> None:
        self.window.apply_slot_dto(self.slot_index, self.empty_dto, clear=True)

    def undo(self) -> None:
        self.window.apply_slot_dto(self.slot_index, self.old_dto)


class SwapButtonsCommand(QUndoCommand):
    """Обмен или копирование кнопок между слотами при Drag-and-Drop."""

    def __init__(
        self,
        window: DeckEditorWindow,
        src_slot: int,
        dst_slot: int,
        is_copy: bool = False,
        text: str = "Swap Buttons",
    ) -> None:
        super().__init__(text)
        self.window = window
        self.src_slot = src_slot
        self.dst_slot = dst_slot
        self.is_copy = is_copy

        src_dto = window.get_slot_dto(src_slot)
        dst_dto = window.get_slot_dto(dst_slot)
        self.old_src = (
            src_dto.model_copy(deep=True)
            if src_dto
            else ButtonSlotDTO(slot_index=src_slot)
        )
        self.old_dst = (
            dst_dto.model_copy(deep=True)
            if dst_dto
            else ButtonSlotDTO(slot_index=dst_slot)
        )

    def redo(self) -> None:
        if self.is_copy:
            new_dst = self.old_src.model_copy(deep=True)
            new_dst.slot_index = self.dst_slot
            self.window.apply_slot_dto(self.dst_slot, new_dst)
        else:
            new_dst = self.old_src.model_copy(deep=True)
            new_dst.slot_index = self.dst_slot
            new_src = self.old_dst.model_copy(deep=True)
            new_src.slot_index = self.src_slot
            self.window.apply_slot_dto(self.src_slot, new_src)
            self.window.apply_slot_dto(self.dst_slot, new_dst)

    def undo(self) -> None:
        self.window.apply_slot_dto(self.src_slot, self.old_src)
        self.window.apply_slot_dto(self.dst_slot, self.old_dst)


class UpdatePropertyCommand(QUndoCommand):
    """Атомарное изменение отдельного свойства кнопки."""

    def __init__(
        self,
        window: DeckEditorWindow,
        slot_index: int,
        prop_name: str,
        new_val: Any,
        old_val: Any,
        text: str = "Update Property",
    ) -> None:
        super().__init__(text)
        self.window = window
        self.slot_index = slot_index
        self.prop_name = prop_name
        self.new_val = new_val
        self.old_val = old_val

    def redo(self) -> None:
        self.window.apply_property_value(self.slot_index, self.prop_name, self.new_val)

    def undo(self) -> None:
        self.window.apply_property_value(self.slot_index, self.prop_name, self.old_val)


__all__ = [
    "AssignActionCommand",
    "ClearSlotCommand",
    "SwapButtonsCommand",
    "UpdatePropertyCommand",
]
