import json
import os
from typing import Dict, Any, Optional

def load_mapping(mapping_file: str) -> Dict[str, Any]:
    """Загружает сопоставления задач из файла"""
    if os.path.exists(mapping_file):
        with open(mapping_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_mapping(mapping: Dict[str, Any], mapping_file: str) -> None:
    """Сохраняет сопоставления задач в файл"""
    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

def compute_todo_hash(task: Dict[str, Any]) -> str:
    """Вычисляет хэш задачи Microsoft To Do"""
    desc = (task.get("body") or {}).get("content") or ""
    due = task.get("dueDateTime", {}).get("dateTime")
    due_str = due.split("T")[0] if due else ""
    return f"{task['title']}|{desc}|{due_str}|{task['status']}"

def compute_kaiten_hash(card: Dict[str, Any]) -> str:
    """Вычисляет хэш карточки Kaiten"""
    desc = card.get("description") or ""
    due_raw = card.get("due_date") or ""
    # Нормализуем дату из Kaiten к формату YYYY-MM-DD
    if due_raw and "T" in due_raw:
        due = due_raw.split("T")[0]
    else:
        due = due_raw
    status = "completed" if card.get("state") == 2 else "notStarted"
    return f"{card['title']}|{desc}|{due}|{status}"

def todo_date_to_kaiten_date(todo_due: str) -> Optional[str]:
    """Конвертирует дату из формата To Do в формат Kaiten"""
    if not todo_due:
        return None
    return todo_due.split("T")[0]

def kaiten_date_to_todo_date(kaiten_due: str) -> Optional[str]:
    """Конвертирует дату из формата Kaiten в формат To Do"""
    if not kaiten_due:
        return None
    return f"{kaiten_due}T10:00.0000000"
