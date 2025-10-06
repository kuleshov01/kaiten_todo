import os
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class Config:
    """Класс конфигурации приложения"""
    
    # Microsoft To Do
    MS_CLIENT_ID: str = os.getenv("MS_CLIENT_ID")
    AUTHORITY: str = "https://login.microsoftonline.com/consumers"
    SCOPE: list = ["Tasks.ReadWrite"]
    CACHE_FILE: str = "token_cache.bin"
    
    # Kaiten
    KAITEN_TOKEN: str = os.getenv("KAITEN_API_TOKEN")
    KAITEN_DOMAIN: str = os.getenv("KAITEN_DOMAIN")
    KAITEN_SPACE_ID: str = os.getenv("KAITEN_SPACE_ID")
    KAITEN_BOARD_ID: int = int(os.getenv("KAITEN_BOARD_ID"))
    KAITEN_COLUMN_ID: int = int(os.getenv("KAITEN_COLUMN_ID"))
    KAITEN_API_BASE: str = f"https://{KAITEN_DOMAIN}/api/latest"
    
    # Синхронизация
    MAPPING_FILE: str = "sync_mapping.json"
    SYNC_LIST_NAME: str = "Задачи"
    
    @classmethod
    def validate(cls) -> bool:
        """Проверяет, все ли необходимые переменные окружения заданы"""
        required_vars = [
            cls.MS_CLIENT_ID,
            cls.KAITEN_TOKEN,
            cls.KAITEN_DOMAIN,
            cls.KAITEN_SPACE_ID,
            cls.KAITEN_BOARD_ID,
            cls.KAITEN_COLUMN_ID
        ]
        
        for var in required_vars:
            if var is None:
                return False
        return True

    @classmethod
    def get_missing_vars(cls) -> list:
        """Возвращает список отсутствующих переменных окружения"""
        required_vars = {
            'MS_CLIENT_ID': cls.MS_CLIENT_ID,
            'KAITEN_API_TOKEN': cls.KAITEN_TOKEN,
            'KAITEN_DOMAIN': cls.KAITEN_DOMAIN,
            'KAITEN_SPACE_ID': cls.KAITEN_SPACE_ID,
            'KAITEN_BOARD_ID': cls.KAITEN_BOARD_ID,
            'KAITEN_COLUMN_ID': cls.KAITEN_COLUMN_ID
        }
        
        missing = []
        for name, value in required_vars.items():
            if value is None:
                missing.append(name)
        return missing