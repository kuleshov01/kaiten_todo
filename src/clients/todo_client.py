#!/usr/bin/env python3
"""
Модуль клиента Microsoft To Do для приложения синхронизации
"""

import os
from typing import Dict, Optional, Any
import logging

from src.exceptions.exceptions import MicrosoftTodoError
from src.config.config import Config


logger = logging.getLogger(__name__)


class MicrosoftTodoClient:
    def __init__(self, config: Config):
        self.config = config
        self.token = None
        self.list_id = None

    def get_access_token(self) -> str:
        import msal
        cache = self._load_cache()
        app = msal.PublicClientApplication(self.config.MS_CLIENT_ID, authority=self.config.AUTHORITY, token_cache=cache)
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(self.config.SCOPE, account=accounts[0])
            if result and "access_token" in result:
                self._save_cache(cache)
                return result["access_token"]
        
        logger.info("Требуется авторизация в Microsoft...")
        flow = app.initiate_device_flow(scopes=self.config.SCOPE)
        logger.info(f"Перейдите по ссылке и введите код:\n{flow['message']}")
        result = app.acquire_token_by_device_flow(flow)
        if "access_token" in result:
            self._save_cache(cache)
            return result["access_token"]
        else:
            raise MicrosoftTodoError(f"Ошибка авторизации: {result.get('error_description')}")

    def _load_cache(self):
        import msal
        cache = msal.SerializableTokenCache()
        if os.path.exists(self.config.CACHE_FILE):
            with open(self.config.CACHE_FILE, "r") as f:
                cache.deserialize(f.read())
        return cache

    def _save_cache(self, cache):
        import msal
        if cache.has_state_changed:
            with open(self.config.CACHE_FILE, "w") as f:
                f.write(cache.serialize())

    def get_list_id(self, access_token: str) -> str:
        import requests
        resp = requests.get(
            "https://graph.microsoft.com/v1.0/me/todo/lists", 
            headers={"Authorization": f"Bearer {access_token}"}
        )
        resp.raise_for_status()
        for lst in resp.json()["value"]:
            if lst["displayName"] == self.config.SYNC_LIST_NAME:
                return lst["id"]
        raise MicrosoftTodoError(f"Список '{self.config.SYNC_LIST_NAME}' не найден")

    def get_active_tasks(self, access_token: str, list_id: str) -> Dict[str, Any]:
        import requests
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
        import requests
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
                    title: str, description: str = None, due_date: str = None, status: str = "notStarted") -> Optional[str]:
        import requests
        url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks"
        payload = {
            "title": title,
            "status": status
        }
        
        if description:
            payload["body"] = {"content": description, "contentType": "text"}
        # Проверяем, что дата не пустая и не содержит недопустимых значений
        if due_date and due_date != "None" and due_date != "null":
            # Проверяем, что дата в правильном формате
            if "T" in due_date:
                payload["dueDateTime"] = {"dateTime": due_date, "timeZone": "UTC"}
            else:
                # Если дата в формате YYYY-MM-DD, добавляем время
                payload["dueDateTime"] = {"dateTime": f"{due_date}T00:00:00.000Z", "timeZone": "UTC"}
        
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        resp = requests.post(url, json=payload, headers=headers)
        
        if resp.status_code == 201:
            task_id = resp.json()["id"]
            logger.info(f"✅ To Do ← Kaiten | Создана задача: '{title}' (ID: {task_id})")
            return task_id
        else:
            logger.error(f"❌ Не удалось создать задачу в To Do: {resp.status_code} {resp.text[:200]}")
            return None