"""
Единый автоматизированный линтер и валидатор интернационализации (i18n linter & validator).
Объединяет проверку контрактов словарей locales/*.json и AST-сканирование UI-кода:
1. Синтаксическая валидность JSON файлов (ru.json, en.json).
2. Наличие 8 обязательных пространств имен (common, sidebar, audio, deck, telemetry, media, settings, showcase).
3. 100% паритет ключей между русским и английским словарями (diff == 0).
4. Корректность структур плюрализации (RU: one/few/many, EN: one/other) и наличие {count}.
5. Идентичность именованных параметров интерполяции {param} между языками.
6. AST-сканирование исходных кодов ui/ и modules/ на отсутствие прямого хардкода кириллических строк.
"""
import ast
import json
import re
from pathlib import Path
from typing import Any, Set

import pytest

from core.i18n.manager import _flatten_dict, _is_plural_leaf


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOCALES_DIR = PROJECT_ROOT / "locales"
RU_PATH = LOCALES_DIR / "ru.json"
EN_PATH = LOCALES_DIR / "en.json"

REQUIRED_NAMESPACES = {
    "common",
    "sidebar",
    "audio",
    "deck",
    "telemetry",
    "media",
    "settings",
    "showcase",
}

PLACEHOLDER_REGEX = re.compile(r"\{([a-zA-Z0-9_]+)\}")


def extract_placeholders(value: Any) -> Set[str]:
    """Извлечение всех именованных параметров {var} из строки или блока плюрализации."""
    if isinstance(value, str):
        return set(PLACEHOLDER_REGEX.findall(value))
    elif isinstance(value, dict):
        placeholders: Set[str] = set()
        for sub_val in value.values():
            if isinstance(sub_val, str):
                placeholders.update(PLACEHOLDER_REGEX.findall(sub_val))
        return placeholders
    return set()


def test_locales_files_exist_and_valid_json():
    """Проверка существования файлов и корректности их JSON синтаксиса."""
    assert RU_PATH.exists(), f"Файл {RU_PATH} не найден"
    assert EN_PATH.exists(), f"Файл {EN_PATH} не найден"

    with open(RU_PATH, "r", encoding="utf-8") as f:
        ru_data = json.load(f)
    assert isinstance(ru_data, dict), "ru.json должен быть корневым JSON объектом"

    with open(EN_PATH, "r", encoding="utf-8") as f:
        en_data = json.load(f)
    assert isinstance(en_data, dict), "en.json должен быть корневым JSON объектом"


def test_locales_required_namespaces():
    """Проверка наличия всех 8 обязательных пространств имен."""
    with open(RU_PATH, "r", encoding="utf-8") as f:
        ru_data = json.load(f)
    with open(EN_PATH, "r", encoding="utf-8") as f:
        en_data = json.load(f)

    ru_namespaces = set(ru_data.keys())
    en_namespaces = set(en_data.keys())

    assert REQUIRED_NAMESPACES.issubset(ru_namespaces), (
        f"ru.json отсутствуют пространства: {REQUIRED_NAMESPACES - ru_namespaces}"
    )
    assert REQUIRED_NAMESPACES.issubset(en_namespaces), (
        f"en.json отсутствуют пространства: {REQUIRED_NAMESPACES - en_namespaces}"
    )


def test_i18n_dictionary_parity():
    """Проверка 100% паритета ключей между ru.json и en.json (diff == 0)."""
    with open(RU_PATH, "r", encoding="utf-8") as f:
        ru_data = json.load(f)
    with open(EN_PATH, "r", encoding="utf-8") as f:
        en_data = json.load(f)

    ru_flat = _flatten_dict(ru_data)
    en_flat = _flatten_dict(en_data)

    ru_keys = set(ru_flat.keys())
    en_keys = set(en_flat.keys())

    diff = ru_keys ^ en_keys
    assert len(diff) == 0, f"Расхождение ключей между ru.json и en.json ({len(diff)}): {diff}"


def test_locales_pluralization_structure():
    """Проверка корректности структуры блоков плюрализации для RU и EN."""
    with open(RU_PATH, "r", encoding="utf-8") as f:
        ru_flat = _flatten_dict(json.load(f))
    with open(EN_PATH, "r", encoding="utf-8") as f:
        en_flat = _flatten_dict(json.load(f))

    for key, val in ru_flat.items():
        if _is_plural_leaf(val):
            # Проверка RU: формы one, few, many
            assert "one" in val, f"RU плюральный блок '{key}' не содержит 'one'"
            assert "few" in val, f"RU плюральный блок '{key}' не содержит 'few'"
            assert "many" in val, f"RU плюральный блок '{key}' не содержит 'many'"

            # Соответствующий EN блок
            en_val = en_flat[key]
            assert _is_plural_leaf(en_val), f"EN ключ '{key}' должен быть плюральным блоком"
            assert "one" in en_val, f"EN плюральный блок '{key}' не содержит 'one'"
            assert "other" in en_val, f"EN плюральный блок '{key}' не содержит 'other'"

            # Плейсхолдер {count} в каждой форме
            for cat, text in val.items():
                assert "{count}" in text, f"RU '{key}.{cat}' не содержит {{count}}"
            for cat, text in en_val.items():
                assert "{count}" in text, f"EN '{key}.{cat}' не содержит {{count}}"


def test_i18n_interpolation_placeholders_consistency():
    """Проверка идентичности именованных параметров {var} между ru.json и en.json."""
    with open(RU_PATH, "r", encoding="utf-8") as f:
        ru_flat = _flatten_dict(json.load(f))
    with open(EN_PATH, "r", encoding="utf-8") as f:
        en_flat = _flatten_dict(json.load(f))

    mismatches = []
    for key in set(ru_flat.keys()) & set(en_flat.keys()):
        ru_placeholders = extract_placeholders(ru_flat[key])
        en_placeholders = extract_placeholders(en_flat[key])
        if ru_placeholders != en_placeholders:
            mismatches.append(
                f"Ключ '{key}': RU={ru_placeholders} != EN={en_placeholders}"
            )

    assert not mismatches, "Обнаружены несоответствия плейсхолдеров:\n" + "\n".join(mismatches)


def test_i18n_ast_no_hardcoded_cyrillic_in_ui():
    """
    AST-сканер: подтверждает отсутствие прямых строковых литералов на кириллице
    в вызовах методов отображения (setText, setToolTip, setTitle, QLabel, QPushButton)
    внутри директорий ui/ и modules/.
    """
    cyrillic_pattern = re.compile(r"[\u0400-\u04FF]")
    checked_calls = {"setText", "setToolTip", "setTitle", "QLabel", "QPushButton"}
    violations = []

    for folder in ["ui", "modules"]:
        folder_path = PROJECT_ROOT / folder
        for py_file in folder_path.rglob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                source = f.read()

            try:
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError as e:
                pytest.fail(f"Синтаксическая ошибка в {py_file}: {e}")

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr

                    if func_name in checked_calls:
                        for arg in node.args:
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                if cyrillic_pattern.search(arg.value):
                                    violations.append((
                                        py_file.relative_to(PROJECT_ROOT).as_posix(),
                                        node.lineno,
                                        func_name,
                                        arg.value,
                                    ))
                            elif isinstance(arg, ast.JoinedStr):
                                for part in arg.values:
                                    if isinstance(part, ast.Constant) and isinstance(part.value, str):
                                        if cyrillic_pattern.search(part.value):
                                            violations.append((
                                                py_file.relative_to(PROJECT_ROOT).as_posix(),
                                                node.lineno,
                                                func_name,
                                                part.value,
                                            ))

    msg = "\n".join(f"{f}:{line} in {fn}(): '{val}'" for f, line, fn, val in violations)
    assert not violations, f"Обнаружен прямой хардкод кириллицы в UI-вызовах ({len(violations)} мест):\n{msg}"
