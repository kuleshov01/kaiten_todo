import os
from datetime import datetime
from typing import Dict, Optional, Any

from dotenv import load_dotenv
import logging

from src.config import Config
from src.utils import (
    load_mapping, save_mapping, 
    compute_todo_hash, compute_kaiten_hash,
    todo_date_to_kaiten_date, kaiten_date_to_todo_date
)
from src.exceptions import SyncError, MicrosoftTodoError, KaitenError

# === Логирование ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("sync.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# === Проверка конфигурации ===
if not Config.validate():
    missing_vars = Config.get_missing_vars()
    logger.error(f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
    raise ValueError(f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")

# === Импорты после проверки конфигурации ===
import msal
import requests

# === Классы для работы с API ===
class MicrosoftTodoClient:
    def __init__(self):
        self.token = None
        self.list_id = None

    def get_access_token(self) -> str:
        cache = self._load_cache()
        app = msal.PublicClientApplication(Config.MS_CLIENT_ID, authority=Config.AUTHORITY, token_cache=cache)
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(Config.SCOPE, account=accounts[0])
            if result and "access_token" in result:
                self._save_cache(cache)
                return result["access_token"]
        
        logger.info("Требуется авторизация в Microsoft...")
        flow = app.initiate_device_flow(scopes=Config.SCOPE)
        logger.info(f"Перейдите по ссылке и введите код:\n{flow['message']}")
        result = app.acquire_token_by_device_flow(flow)
        if "access_token" in result:
            self._save_cache(cache)
            return result["access_token"]
        else:
            raise MicrosoftTodoError(f"Ошибка авторизации: {result.get('error_description')}")

    def _load_cache(self):
        cache = msal.SerializableTokenCache()
        if os.path.exists(Config.CACHE_FILE):
            with open(Config.CACHE_FILE, "r") as f:
                cache.deserialize(f.read())
        return cache

    def _save_cache(self, cache):
        if cache.has_state_changed:
            with open(Config.CACHE_FILE, "w") as f:
                f.write(cache.serialize())

    def get_list_id(self, access_token: str) -> str:
        resp = requests.get(
            "https://graph.microsoft.com/v1.0/me/todo/lists", 
            headers={"Authorization": f"Bearer {access_token}"}
        )
        resp.raise_for_status()
        for lst in resp.json()["value"]:
            if lst["displayName"] == Config.SYNC_LIST_NAME:
                return lst["id"]
        raise MicrosoftTodoError(f"Список '{Config.SYNC_LIST_NAME}' не найден")

    def get_active_tasks(self, access_token: str, list_id: str) -> Dict[str, Any]:
        resp = requests.get(
            f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks", 
            headers={"Authorization": f"Bearer {access_token}"}
        )
        resp.raise_for_status()
        tasks = resp.json()["value"]
        return {t["id"]: t for t in tasks if t["status"] in ("notStarted", "inProgress", "completed")}

    def update_task(self, access_token: str, list_id: str, task_id: str, 
                    title: str = None, description: str = None, 
                    due_date: str = None, status: str = None) -> bool:
        url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks/{task_id}"
        payload = {}
        changes = []
        
        if title is not None:
            payload["title"] = title
            changes.append(f"title='{title}'")
        if description is not None:
            payload["body"] = {"content": description or "", "contentType": "text"}
            changes.append(f"description='{(description or '')[:30]}...'")  # Обрезаем для лога
        if due_date is not None:
            if due_date:
                payload["dueDateTime"] = {"dateTime": due_date, "timeZone": "UTC"}
            else:
                payload["dueDateTime"] = None
            changes.append(f"due_date={due_date}")
        if status is not None:
            payload["status"] = status
            changes.append(f"status={status}")
        
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        resp = requests.patch(url, json=payload, headers=headers)
        
        if resp.status_code == 200:
            logger.info(f"✅ To Do ← Kaiten | Обновлена задача '{task_id}': {', '.join(changes)}")
            return True
        else:
            logger.error(f"❌ Не удалось обновить задачу в To Do: {resp.status_code} {resp.text[:200]}")
            return False

    def create_task(self, access_token: str, list_id: str, 
                    title: str, description: str = None, due_date: str = None) -> Optional[str]:
        url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks"
        payload = {
            "title": title,
            "status": "notStarted"
        }
        
        if description:
            payload["body"] = {"content": description, "contentType": "text"}
        if due_date:
            payload["dueDateTime"] = {"dateTime": due_date, "timeZone": "UTC"}
        
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        resp = requests.post(url, json=payload, headers=headers)
        
        if resp.status_code == 201:
            task_id = resp.json()["id"]
            logger.info(f"✅ To Do ← Kaiten | Создана задача: '{title}' (ID: {task_id})")
            return task_id
        else:
            logger.error(f"❌ Не удалось создать задачу в To Do: {resp.status_code} {resp.text[:200]}")
            return None


class KaitenClient:
    def __init__(self):
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {Config.KAITEN_TOKEN}",
            "User-Agent": "PostmanRuntime/7.32.3"
        }

    def get_cards(self) -> Dict[str, Any]:
        url = f"{Config.KAITEN_API_BASE}/spaces/{Config.KAITEN_SPACE_ID}/boards/{Config.KAITEN_BOARD_ID}"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        cards = resp.json().get("cards", [])
        return {c["id"]: c for c in cards if c.get("column_id") == Config.KAITEN_COLUMN_ID}

    def create_card(self, title: str, description: str = None, due_date: str = None) -> Optional[int]:
        payload = {
            "title": title,
            "description": description or "",
            "board_id": Config.KAITEN_BOARD_ID,
            "column_id": Config.KAITEN_COLUMN_ID,
            "due_date": due_date,
            "priority": 1
        }
        
        headers = {
            "Authorization": f"Bearer {Config.KAITEN_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "PostmanRuntime/7.32.3"
        }
        
        resp = requests.post(f"{Config.KAITEN_API_BASE}/cards", json=payload, headers=headers)
        if resp.status_code == 200:
            card_id = resp.json()["id"]
            logger.info(f"✅ Kaiten ← To Do | Создана карточка: '{title}' (ID: {card_id})")
            return card_id
        else:
            logger.error(f"❌ Не удалось создать карточку в Kaiten: {resp.status_code} {resp.text[:200]}")
            return None

    def update_card(self, card_id: int, title: str = None, 
                    description: str = None, due_date: str = None) -> bool:
        payload = {}
        changes = []
        
        if title is not None:
            payload["title"] = title
            changes.append(f"title='{title}'")
        if description is not None:
            payload["description"] = description or ""
            changes.append(f"description='{(description or '')[:30]}...'")  # Обрезаем для лога
        if due_date is not None:
            payload["due_date"] = due_date
            changes.append(f"due_date={due_date}")
        
        headers = {
            "Authorization": f"Bearer {Config.KAITEN_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "PostmanRuntime/7.32.3"
        }
        
        resp = requests.patch(f"{Config.KAITEN_API_BASE}/cards/{card_id}", json=payload, headers=headers)
        if resp.status_code == 200:
            logger.info(f"✅ Kaiten ← To Do | Обновлена карточка {card_id}: {', '.join(changes)}")
            return True
        else:
            logger.error(f"❌ Не удалось обновить карточку {card_id} в Kaiten: {resp.status_code} {resp.text[:200]}")
            return False

    def delete_card(self, card_id: int) -> bool:
        headers = {"Authorization": f"Bearer {Config.KAITEN_TOKEN}", "User-Agent": "PostmanRuntime/7.32.3"}
        resp = requests.delete(f"{Config.KAITEN_API_BASE}/cards/{card_id}", headers=headers)
        if resp.status_code == 204:
            logger.info(f"🗑️ Kaiten ← To Do | Удалена карточка {card_id}")
            return True
        else:
            logger.error(f"❌ Не удалось удалить карточку {card_id}: {resp.status_code} {resp.text[:200]}")
            return False


class SyncEngine:
    def __init__(self):
        self.todo_client = MicrosoftTodoClient()
        self.kaiten_client = KaitenClient()

    def sync(self) -> None:
        logger.info("🔄 Запуск синхронизации To Do ↔ Kaiten")
        
        try:
            # Получаем токен и ID списка To Do
            token = self.todo_client.get_access_token()
            list_id = self.todo_client.get_list_id(token)
            
            # Получаем текущие задачи и карточки
            todo_tasks = self.todo_client.get_active_tasks(token, list_id)
            kaiten_cards = self.kaiten_client.get_cards()
            mapping = load_mapping(Config.MAPPING_FILE)

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
                    t_due = todo_date_to_kaiten_date(todo.get("dueDateTime", {}).get("dateTime"))
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
                    self.todo_client.update_task(
                        token, list_id, todo_id,
                        title=card["title"],
                        description=k_desc,
                        due_date=kaiten_date_to_todo_date(k_due) if k_due else None,
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
                t_due = todo_date_to_kaiten_date(todo.get("dueDateTime", {}).get("dateTime"))
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

            # Удаление задач
            for todo_id, meta in list(mapping.items()):
                if todo_id not in todo_tasks:
                    if self.kaiten_client.delete_card(meta["kaiten_card_id"]):
                        del mapping[todo_id]

            save_mapping(mapping, Config.MAPPING_FILE)
            logger.info("✅ Синхронизация завершена успешно")
            
        except MicrosoftTodoError as e:
            logger.error(f"❌ Ошибка Microsoft To Do: {e}")
        except KaitenError as e:
            logger.error(f"❌ Ошибка Kaiten: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Ошибка HTTP запроса: {e}")
        except Exception as e:
            logger.exception(f"❌ Критическая ошибка: {e}")


# === Запуск ===
if __name__ == "__main__":
    sync_engine = SyncEngine()
    sync_engine.sync()