#!/usr/bin/env python3
"""
Модуль клиента Kaiten для приложения синхронизации
"""

from typing import Dict, Optional, Any
import logging

try:
    from src.exceptions.exceptions import KaitenError
    from src.config.config import Config
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from exceptions.exceptions import KaitenError
    from config.config import Config


logger = logging.getLogger(__name__)


class KaitenClient:
    def __init__(self, config: Config):
        self.config = config
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {config.KAITEN_TOKEN}",
            "User-Agent": "PostmanRuntime/7.32.3"
        }

    def get_cards(self) -> Dict[str, Any]:
        import requests
        url = f"{self.config.KAITEN_API_BASE}/spaces/{self.config.KAITEN_SPACE_ID}/boards/{self.config.KAITEN_BOARD_ID}"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        cards = resp.json().get("cards", [])
        return {c["id"]: c for c in cards if c.get("column_id") == self.config.KAITEN_COLUMN_ID}

    def create_card(self, title: str, description: str = None, due_date: str = None) -> Optional[int]:
        import requests
        payload = {
            "title": title,
            "description": description or "",
            "board_id": self.config.KAITEN_BOARD_ID,
            "column_id": self.config.KAITEN_COLUMN_ID,
            "due_date": due_date,
            "priority": 1
        }
        
        headers = {
            "Authorization": f"Bearer {self.config.KAITEN_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "PostmanRuntime/7.32.3"
        }
        
        resp = requests.post(f"{self.config.KAITEN_API_BASE}/cards", json=payload, headers=headers)
        if resp.status_code == 200:
            card_id = resp.json()["id"]
            logger.info(f"✅ Kaiten ← To Do | Создана карточка: '{title}' (ID: {card_id})")
            return card_id
        else:
            logger.error(f"❌ Не удалось создать карточку в Kaiten: {resp.status_code} {resp.text[:200]}")
            return None

    def update_card(self, card_id: int, title: str = None, 
                    description: str = None, due_date: str = None) -> bool:
        import requests
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
            "Authorization": f"Bearer {self.config.KAITEN_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "PostmanRuntime/7.32.3"
        }
        
        resp = requests.patch(f"{self.config.KAITEN_API_BASE}/cards/{card_id}", json=payload, headers=headers)
        if resp.status_code == 200:
            logger.info(f"✅ Kaiten ← To Do | Обновлена карточка {card_id}: {', '.join(changes)}")
            return True
        else:
            logger.error(f"❌ Не удалось обновить карточку {card_id} в Kaiten: {resp.status_code} {resp.text[:200]}")
            return False

    def delete_card(self, card_id: int) -> bool:
       import requests
       headers = {"Authorization": f"Bearer {self.config.KAITEN_TOKEN}", "User-Agent": "PostmanRuntime/7.32.3"}
       resp = requests.delete(f"{self.config.KAITEN_API_BASE}/cards/{card_id}", headers=headers)
       # Kaiten API архивирует карточки вместо их физического удаления, возвращая 200 OK
       # и тело ответа с полем "archived": true
       if resp.status_code == 204:
           logger.info(f"🗑️ Kaiten ← To Do | Удалена карточка {card_id}")
           return True
       elif resp.status_code == 200:
           # Проверяем, действительно ли карточка была заархивирована
           try:
               response_data = resp.json()
               if response_data.get("archived", False):
                   logger.info(f"🗑️ Kaiten ← To Do | Карточка {card_id} заархивирована (удалена)")
                   return True
               else:
                   logger.error(f"❌ Не удалось удалить карточку {card_id}: карточка не заархивирована")
                   return False
           except:
               # Если не удалось распарсить JSON, но статус 200, считаем, что карточка заархивирована
               logger.info(f"🗑️ Kaiten ← To Do | Карточка {card_id} заархивирована (удалена)")
               return True
       else:
           logger.error(f"❌ Не удалось удалить карточку {card_id}: {resp.status_code} {resp.text[:200]}")
           return False