"""
Процессор плюрализации для русской (RU) и английской (EN) локалей.
Определяет грамматические числовые категории для подстановки верных окончаний и форм.
"""
from typing import Union

Number = Union[int, float]


def get_plural_category_ru(count: Number) -> str:
    """
    Вычисляет грамматическую числовую категорию для русского языка.

    Категории:
    - one: оканчивается на 1, кроме 11 (1, 21, 31, 101 устройство)
    - few: оканчивается на 2-4, кроме 12-14 (2, 3, 4, 22, 104 устройства)
    - many: все остальные случаи (0, 5-20, 25-30, 111-114 устройств)
    """
    abs_count = abs(int(count))
    rem10 = abs_count % 10
    rem100 = abs_count % 100

    if rem10 == 1 and rem100 != 11:
        return "one"
    if 2 <= rem10 <= 4 and not (12 <= rem100 <= 14):
        return "few"
    return "many"


def get_plural_category_en(count: Number) -> str:
    """
    Вычисляет грамматическую числовую категорию для английского языка.

    Категории:
    - one: ровно 1 (1 device)
    - other: все остальные случаи (0, 2, 5 devices)
    """
    abs_count = abs(int(count))
    if abs_count == 1:
        return "one"
    return "other"


def resolve_plural_category(lang: str, count: Number) -> str:
    """
    Единый диспетчер разрешения категории множественного числа.
    Поддерживает языки 'ru' и 'en'. При неизвестном языке использует английский каскад.
    """
    norm_lang = (lang or "").lower().strip()
    if norm_lang == "ru":
        return get_plural_category_ru(count)
    if norm_lang == "en":
        return get_plural_category_en(count)
    return get_plural_category_en(count)


__all__ = [
    "get_plural_category_ru",
    "get_plural_category_en",
    "resolve_plural_category",
]
