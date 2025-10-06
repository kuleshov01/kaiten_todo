import json
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import re

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
    due_datetime = task.get("dueDateTime")
    due = due_datetime.get("dateTime") if due_datetime else None
    
    if due:
        # Конвертируем дату из UTC в сахалинское время для правильного извлечения даты
        from datetime import datetime, timezone, timedelta
        try:
            if due.endswith("Z"):
                utc_time_str = due[:-1]  # Убираем Z
                dt = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(due)
            
            # Убедимся, что дата имеет информацию о часовом поясе
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            # Часовой пояс Сахалинска (UTC+11:00)
            sakhalin_tz = timezone(timedelta(hours=11))
            
            # Преобразуем время из UTC в сахалинское
            sakhalin_time = dt.astimezone(sakhalin_tz)
            
            # Извлекаем только дату
            due_str = sakhalin_time.date().isoformat()
        except:
            # Если формат даты некорректен, просто извлекаем дату
            due_str = due.split("T")[0]
    else:
        due_str = ""
    
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
    """Конвертирует дату из формата To Do в формат Kaiten с учетом часового пояса Сахалинска (UTC+11)"""
    if not todo_due:
        return None
    
    from datetime import timedelta, timezone
    
    try:
        # Разбираем строку даты/времени из формата ISO
        if todo_due.endswith("Z"):
            # Если строка заканчивается на Z, это UTC время
            utc_time_str = todo_due[:-1] # Убираем Z
            dt = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        else:
            # Microsoft To Do может возвращать дату в формате с лишними нулями, например, 2025-10-05T13:00:00.0000000
            # Попробуем нормализовать формат
            if ".0000" in todo_due:
                # Убираем лишние нули и заменяем на Z
                utc_time_str = todo_due.replace(".00000", ".000Z")
                dt = datetime.fromisoformat(utc_time_str)
            elif ".0000" in todo_due:
                # Убираем лишние нули и заменяем на Z
                utc_time_str = todo_due.replace(".0000", ".000Z")
            else:
                dt = datetime.fromisoformat(todo_due)
        
        # Убедимся, что дата имеет информацию о часовом поясе
        if dt.tzinfo is None:
            # Если в строке не было информации о часовом поясе, предполагаем, что это UTC
            dt = dt.replace(tzinfo=timezone.utc)
        
        # Часовой пояс Сахалинска (UTC+11:00)
        sakhalin_tz = timezone(timedelta(hours=11))
        
        # Преобразуем время из UTC в сахалинское
        sakhalin_time = dt.astimezone(sakhalin_tz)
        
        # Для Kaiten возвращаем только дату в формате YYYY-MM-DD
        result = sakhalin_time.date().isoformat()
        print(f"DEBUG: todo_date_to_kaiten_date: {todo_due} -> {result}")
        return result
    except ValueError:
        # Если формат даты некорректен, возвращаем только дату
        if "T" in todo_due:
            result = todo_due.split("T")[0]
        else:
            result = todo_due
        print(f"DEBUG: todo_date_to_kaiten_date (fallback): {todo_due} -> {result}")
        return result

def kaiten_date_to_todo_date(kaiten_due: str) -> Optional[str]:
    """Конвертирует дату из формата Kaiten в формат To Do, сохраняя дневной формат даты"""
    if not kaiten_due:
        return None
    
    from datetime import timedelta, timezone
    
    # Если дата уже содержит время (в формате ISO), просто конвертируем из сахалинского времени в UTC
    if "T" in kaiten_due:
        try:
            # Предполагаем, что время из Kaiten - это сахалинское (UTC+11)
            dt = datetime.fromisoformat(kaiten_due)
            if dt.tzinfo is None:
                # Если нет информации о часовом поясе, считаем, что это сахалинское время
                sakhalin_tz = timezone(timedelta(hours=11))
                dt = dt.replace(tzinfo=sakhalin_tz)
            
            # Конвертируем сахалинское время в UTC
            utc_time = dt.astimezone(timezone.utc)
            result = utc_time.isoformat().replace('+00:00', 'Z')
            print(f"DEBUG: kaiten_date_to_todo_date: {kaiten_due} -> {result}")
            return result
        except ValueError:
            # Если формат некорректен, возвращаем как есть
            print(f"DEBUG: kaiten_date_to_todo_date (fallback): {kaiten_due} -> {kaiten_due}")
            return kaiten_due
    
    # Для даты без времени, чтобы сохранить дневной формат,
    # передаем дату с 00:00 сахалинского времени, но конвертируем в UTC так,
    # чтобы дата в To Do оставалась той же
    try:
        # Создаем дату с 0:0 сахалинского времени
        sakhalin_tz = timezone(timedelta(hours=11))
        dt = datetime.fromisoformat(f"{kaiten_due}T00:00:00")
        dt = dt.replace(tzinfo=sakhalin_tz)
        
        # Конвертируем в UTC для Microsoft To Do
        utc_time = dt.astimezone(timezone.utc)
        
        # Если дата в UTC отличается от исходной, используем следующий подход:
        # Microsoft To Do может интерпретировать дату по локальному времени пользователя,
        # поэтому просто передаем дату как YYYY-MM-DDT00:00:00Z
        result = f"{kaiten_due}T00:00:00Z"
        print(f"DEBUG: kaiten_date_to_todo_date (date only): {kaiten_due} -> {result}")
        return result
    except ValueError:
        result = f"{kaiten_due}T00:00.000Z"
        print(f"DEBUG: kaiten_date_to_todo_date (fallback date): {kaiten_due} -> {result}")
        return result
