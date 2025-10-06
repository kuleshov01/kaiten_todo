"""
Модуль для планирования регулярной синхронизации задач
"""
import schedule
import time
import logging
from datetime import datetime
from main import SyncEngine

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("sync_scheduler.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_sync():
    """Запускает синхронизацию задач"""
    logger.info("Запуск синхронизации по расписанию")
    try:
        sync_engine = SyncEngine()
        sync_engine.sync()
        logger.info("Синхронизация завершена успешно")
    except Exception as e:
        logger.error(f"Ошибка при синхронизации: {e}")

def start_scheduler():
    """Запускает планировщик синхронизации"""
    # Планируем синхронизацию каждые 30 минут
    schedule.every(30).minutes.do(run_sync)
    
    # Также можно добавить планирование в определенное время
    # schedule.every().hour.at(":00").do(run_sync)  # каждый час в 00 минут
    # schedule.every().day.at("09:00").do(run_sync)  # каждый день в 9:00
    
    logger.info("Планировщик запущен. Синхронизация будет выполняться каждые 30 минут.")
    logger.info("Для остановки нажмите Ctrl+C")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Проверяем каждую минуту
    except KeyboardInterrupt:
        logger.info("Планировщик остановлен пользователем")

if __name__ == "__main__":
    start_scheduler()