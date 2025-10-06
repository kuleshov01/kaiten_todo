#!/usr/bin/env python3
"""
Скрипт для полного сброса синхронизации между Microsoft To Do и Kaiten
"""
import os
import sys
import logging
from typing import Dict, Any

try:
    from src.config.config import Config
    from src.clients.todo_client import MicrosoftTodoClient
    from src.clients.kaiten_client import KaitenClient
    from src.utils.utils import load_mapping, save_mapping
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    from config.config import Config
    from clients.todo_client import MicrosoftTodoClient
    from clients.kaiten_client import KaitenClient
    from utils.utils import load_mapping, save_mapping


def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler("reset_sync.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def reset_sync():
    """Полный сброс синхронизации"""
    logger = setup_logging()
    logger.info("🔄 Начало процесса полного сброса синхронизации")
    
    config = Config()
    todo_client = MicrosoftTodoClient(config)
    kaiten_client = KaitenClient(config)
    
    try:
        # Получаем токен и ID списка To Do
        token = todo_client.get_access_token()
        list_id = todo_client.get_list_id(token)
        
        # Получаем текущие задачи и карточки
        todo_tasks = todo_client.get_active_tasks(token, list_id)
        kaiten_cards = kaiten_client.get_cards()
        
        logger.info(f"ℹ️ Найдено задач в To Do: {len(todo_tasks)}")
        logger.info(f"ℹ️ Найдено карточек в Kaiten: {len(kaiten_cards)}")
        
        # Удаляем все задачи в To Do
        logger.info("🗑️ Удаление всех задач в Microsoft To Do...")
        for todo_id in todo_tasks.keys():
            if todo_client.delete_task(token, list_id, todo_id):
                logger.info(f"✅ Удалена задача To Do: {todo_id}")
            else:
                logger.warning(f"⚠️ Не удалось удалить задачу To Do: {todo_id}")
        
        # Удаляем все карточки в Kaiten
        logger.info("🗑️ Удаление всех карточек в Kaiten...")
        for kaiten_id in kaiten_cards.keys():
            if kaiten_client.delete_card(kaiten_id):
                logger.info(f"✅ Удалена карточка Kaiten: {kaiten_id}")
            else:
                logger.warning(f"⚠️ Не удалось удалить карточку Kaiten: {kaiten_id}")
        
        # Очищаем файл сопоставлений
        if os.path.exists(config.MAPPING_FILE):
            os.remove(config.MAPPING_FILE)
            logger.info("🗑️ Файл сопоставлений удален")
        else:
            logger.info("ℹ️ Файл сопоставлений не найден, пропускаем удаление")
        
        # Создаем пустой файл сопоставлений
        save_mapping({}, config.MAPPING_FILE)
        logger.info("📄 Создан новый пустой файл сопоставлений")
        
        logger.info("✅ Процесс полного сброса синхронизации завершен успешно")
        logger.info("💡 Теперь можно запустить синхронизацию с пустыми списками")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при сбросе синхронизации: {e}")
        raise


if __name__ == "__main__":
    reset_sync()