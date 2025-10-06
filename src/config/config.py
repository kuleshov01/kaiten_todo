#!/usr/bin/env python3
"""
Модуль конфигурации приложения синхронизации Microsoft To Do и Kaiten
"""

import os
from typing import Optional


class Config:
    """Класс конфигурации приложения"""

    def __init__(self):
        # Загружаем переменные окружения из .env файла, если он есть
        if os.path.exists('.env'):
            with open('.env', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value.strip('"\'')
        
        # Microsoft To Do
        self.MS_CLIENT_ID = os.getenv("MS_CLIENT_ID")
        self.AUTHORITY = "https://login.microsoftonline.com/consumers"
        self.SCOPE = ["Tasks.ReadWrite"]
        self.CACHE_FILE = "token_cache.bin"
        
        # Kaiten
        self.KAITEN_TOKEN = os.getenv("KAITEN_API_TOKEN")
        self.KAITEN_DOMAIN = os.getenv("KAITEN_DOMAIN")
        self.KAITEN_SPACE_ID = os.getenv("KAITEN_SPACE_ID")
        self.KAITEN_BOARD_ID = int(os.getenv("KAITEN_BOARD_ID")) if os.getenv("KAITEN_BOARD_ID") else None
        self.KAITEN_COLUMN_ID = int(os.getenv("KAITEN_COLUMN_ID")) if os.getenv("KAITEN_COLUMN_ID") else None
        self.KAITEN_API_BASE = f"https://{self.KAITEN_DOMAIN}/api/latest" if self.KAITEN_DOMAIN else None
        
        # Синхронизация
        self.MAPPING_FILE = "sync_mapping.json"
        self.SYNC_LIST_NAME = "Задачи"

    def validate(self) -> bool:
        """Проверяет, все ли необходимые переменные окружения заданы"""
        return not self.get_missing_vars()

    def get_missing_vars(self) -> list:
        """Возвращает список отсутствующих переменных окружения"""
        required_vars = {
            "MS_CLIENT_ID": self.MS_CLIENT_ID,
            "KAITEN_API_TOKEN": self.KAITEN_TOKEN,
            "KAITEN_DOMAIN": self.KAITEN_DOMAIN,
            "KAITEN_SPACE_ID": self.KAITEN_SPACE_ID,
            "KAITEN_BOARD_ID": self.KAITEN_BOARD_ID,
            "KAITEN_COLUMN_ID": self.KAITEN_COLUMN_ID,
        }

        return [name for name, value in required_vars.items() if value is None]