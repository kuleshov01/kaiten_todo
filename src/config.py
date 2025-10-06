import os
from typing import Optional

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


def _optional_int(value: Optional[str], *, var_name: str) -> Optional[int]:
    """Преобразует строковое значение в int, если оно существует."""

    if value is None:
        return None

    value = value.strip()
    if value == "":
        return None

    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(
            f"Переменная окружения {var_name} должна быть числом"
        ) from exc


class Config:
    """Класс конфигурации приложения"""

    # Microsoft To Do
    MS_CLIENT_ID: Optional[str] = os.getenv("MS_CLIENT_ID")
    AUTHORITY: str = "https://login.microsoftonline.com/consumers"
    SCOPE: list = ["Tasks.ReadWrite"]
    CACHE_FILE: str = "token_cache.bin"

    # Kaiten
    KAITEN_TOKEN: Optional[str] = os.getenv("KAITEN_API_TOKEN")
    KAITEN_DOMAIN: Optional[str] = os.getenv("KAITEN_DOMAIN")
    KAITEN_SPACE_ID: Optional[str] = os.getenv("KAITEN_SPACE_ID")
    _KAITEN_BOARD_ID_RAW: Optional[str] = os.getenv("KAITEN_BOARD_ID")
    _KAITEN_COLUMN_ID_RAW: Optional[str] = os.getenv("KAITEN_COLUMN_ID")
    KAITEN_BOARD_ID: Optional[int] = _optional_int(
        _KAITEN_BOARD_ID_RAW, var_name="KAITEN_BOARD_ID"
    )
    KAITEN_COLUMN_ID: Optional[int] = _optional_int(
        _KAITEN_COLUMN_ID_RAW, var_name="KAITEN_COLUMN_ID"
    )
    KAITEN_API_BASE: Optional[str] = (
        f"https://{KAITEN_DOMAIN}/api/latest" if KAITEN_DOMAIN else None
    )
    
    # Синхронизация
    MAPPING_FILE: str = "sync_mapping.json"
    SYNC_LIST_NAME: str = "Задачи"
    
    @classmethod
    def validate(cls) -> bool:
        """Проверяет, все ли необходимые переменные окружения заданы"""
        return not cls.get_missing_vars()

    @classmethod
    def get_missing_vars(cls) -> list:
        """Возвращает список отсутствующих переменных окружения"""
        required_vars = {
            "MS_CLIENT_ID": cls.MS_CLIENT_ID,
            "KAITEN_API_TOKEN": cls.KAITEN_TOKEN,
            "KAITEN_DOMAIN": cls.KAITEN_DOMAIN,
            "KAITEN_SPACE_ID": cls.KAITEN_SPACE_ID,
            "KAITEN_BOARD_ID": cls.KAITEN_BOARD_ID,
            "KAITEN_COLUMN_ID": cls.KAITEN_COLUMN_ID,
        }

        return [name for name, value in required_vars.items() if value is None]
