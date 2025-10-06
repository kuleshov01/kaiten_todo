#!/usr/bin/env python3
"""
Модуль основного движка синхронизации для приложения синхронизации Microsoft To Do и Kaiten
"""

from typing import Dict, Any
import logging

from src.exceptions.exceptions import MicrosoftTodoError, KaitenError
from src.config.config import Config
from src.utils.utils import load_mapping, save_mapping, compute_todo_hash, compute_kaiten_hash, todo_date_to_kaiten_date, kaiten_date_to_todo_date
from src.clients.todo_client import MicrosoftTodoClient
from src.clients.kaiten_client import KaitenClient


logger = logging.getLogger(__name__)


class SyncEngine:
    def __init__(self, config: Config):
        self.config = config
        self.todo_client = MicrosoftTodoClient(config)
        self.kaiten_client = KaitenClient(config)

    def sync(self) -> None:
        logger.info("🔄 Запуск синхронизации To Do ↔ Kaiten")
        
        try:
            # Получаем токен и ID списка To Do
            token = self.todo_client.get_access_token()
            list_id = self.todo_client.get_list_id(token)
            
            # Получаем текущие задачи и карточки
            todo_tasks = self.todo_client.get_active_tasks(token, list_id)
            kaiten_cards = self.kaiten_client.get_cards()
            mapping = load_mapping(self.config.MAPPING_FILE)

            # Очистка маппинга от удалённых карточек
            new_mapping = {}
            for todo_id, meta in mapping.items():
                kaiten_id = meta["kaiten_card_id"]
                if kaiten_id in kaiten_cards:
                    new_mapping[todo_id] = meta
                else:
                    logger.info(f"ℹ️ Карточка {kaiten_id} удалена вручную — удаляем из маппинга")
            mapping = new_mapping

            # Синхронизация существующих пар
            for todo_id, meta in list(mapping.items()):
                kaiten_id = meta["kaiten_card_id"]
                if todo_id not in todo_tasks or kaiten_id not in kaiten_cards:
                    continue

                todo = todo_tasks[todo_id]
                card = kaiten_cards[kaiten_id]

                current_todo_hash = compute_todo_hash(todo)
                current_kaiten_hash = compute_kaiten_hash(card)

                saved_todo_hash = meta.get("todo_hash", "")
                saved_kaiten_hash = meta.get("kaiten_hash", "")

                # To Do изменился
                if current_todo_hash != saved_todo_hash:
                    t_desc = (todo.get("body") or {}).get("content") or ""
                    original_due = todo.get("dueDateTime", {}).get("dateTime")
                    t_due = todo_date_to_kaiten_date(original_due)
                    logger.debug(f"DEBUG: To Do -> Kaiten | Задача '{todo['title']}' | Оригинальная дата: {original_due} | Конвертированная дата: {t_due}")
                    if self.kaiten_client.update_card(kaiten_id, title=todo["title"], description=t_desc, due_date=t_due):
                        # Сразу обновляем хэш в маппинге, чтобы избежать гонки
                        updated_card = {
                            "title": todo["title"],
                            "description": t_desc,
                            "due_date": t_due or "",
                            "state": 1 # notStarted
                        }
                        meta["kaiten_hash"] = compute_kaiten_hash(updated_card)
                        meta["todo_hash"] = current_todo_hash

                # Kaiten изменился
                elif current_kaiten_hash != saved_kaiten_hash:
                    k_desc = card.get("description") or ""
                    k_due = card.get("due_date")
                    k_status = "completed" if card.get("state") == 2 else "notStarted"
                    converted_due = kaiten_date_to_todo_date(k_due) if k_due else None
                    logger.debug(f"DEBUG: Kaiten -> To Do | Карточка '{card['title']}' | Оригинальная дата: {k_due} | Конвертированная дата: {converted_due}")
                    self.todo_client.update_task(
                        token, list_id, todo_id,
                        title=card["title"],
                        description=k_desc,
                        due_date=converted_due,
                        status=k_status
                    )
                    meta["kaiten_hash"] = current_kaiten_hash
                    meta["todo_hash"] = current_todo_hash

                mapping[todo_id] = meta

            # Создание новых задач
            for todo_id, todo in todo_tasks.items():
                if todo_id in mapping:
                    continue
                if todo["status"] == "completed":
                    continue
                t_desc = (todo.get("body") or {}).get("content") or ""
                original_due = todo.get("dueDateTime", {}).get("dateTime")
                t_due = todo_date_to_kaiten_date(original_due)
                logger.debug(f"DEBUG: NEW TASK To Do -> Kaiten | Задача '{todo['title']}' | Оригинальная дата: {original_due} | Конвертированная дата: {t_due}")
                card_id = self.kaiten_client.create_card(title=todo["title"], description=t_desc, due_date=t_due)
                if card_id:
                    # Эмулируем состояние карточки для корректного хэша
                    fake_card = {
                        "title": todo["title"],
                        "description": t_desc,
                        "due_date": t_due or "",
                        "state": 1
                    }
                    kaiten_hash = compute_kaiten_hash(fake_card)
                    todo_hash = compute_todo_hash(todo)
                    mapping[todo_id] = {
                        "kaiten_card_id": card_id,
                        "todo_hash": todo_hash,
                        "kaiten_hash": kaiten_hash
                    }

            # Создание новых задач из Kaiten в To Do
            for kaiten_id, card in kaiten_cards.items():
                # Проверяем, есть ли уже сопоставление для этой карточки
                todo_id = None
                for t_id, meta in mapping.items():
                    if meta["kaiten_card_id"] == kaiten_id:
                        todo_id = t_id
                        break
                
                # Если карточка Kaiten не имеет соответствующей задачи To Do, создаем новую задачу
                if not todo_id:
                    k_desc = card.get("description") or ""
                    k_due = card.get("due_date")
                    # Определяем статус задачи в To Do на основе статуса карточки Kaiten
                    status = "completed" if card.get("state") == 2 else "notStarted"
                    
                    # Преобразуем дату из формата Kaiten в формат To Do
                    due_date_for_todo = kaiten_date_to_todo_date(k_due) if k_due else None
                    logger.debug(f"DEBUG: NEW TASK Kaiten -> To Do | Карточка '{card['title']}' | Оригинальная дата: {k_due} | Конвертированная дата: {due_date_for_todo}")
                    # Создаем задачу в To Do
                    new_todo_id = self.todo_client.create_task(
                        token,
                        list_id,
                        title=card["title"],
                        description=k_desc,
                        due_date=due_date_for_todo,
                        status=status
                    )
                    
                    if new_todo_id:
                        # Обновляем маппинг
                        fake_todo = {
                            "title": card["title"],
                            "body": {"content": k_desc, "contentType": "text"},
                            "status": status
                        }
                        # Добавляем dueDateTime только если k_due не None
                        if k_due:
                            fake_todo["dueDateTime"] = {"dateTime": kaiten_date_to_todo_date(k_due), "timeZone": "UTC"}
                        todo_hash = compute_todo_hash(fake_todo)
                        kaiten_hash = compute_kaiten_hash(card)
                        mapping[new_todo_id] = {
                            "kaiten_card_id": kaiten_id,
                            "todo_hash": todo_hash,
                            "kaiten_hash": kaiten_hash
                        }

            # Удаление задач
            for todo_id, meta in list(mapping.items()):
                if todo_id not in todo_tasks:
                    if self.kaiten_client.delete_card(meta["kaiten_card_id"]):
                        del mapping[todo_id]

            save_mapping(mapping, self.config.MAPPING_FILE)
            logger.info("✅ Синхронизация завершена успешно")
            
        except MicrosoftTodoError as e:
            logger.error(f"❌ Ошибка Microsoft To Do: {e}")
        except KaitenError as e:
            logger.error(f"❌ Ошибка Kaiten: {e}")
        except Exception as e:
            logger.exception(f"❌ Критическая ошибка: {e}")