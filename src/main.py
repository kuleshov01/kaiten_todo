#!/usr/bin/env python3
"""
Точка входа в приложение синхронизации Microsoft To Do и Kaiten
"""

import sys
import logging

try:
    from src.config.config import Config
    from src.engines.sync_engine import SyncEngine
    from src.engines.force_sync_engine import ForceSyncEngine
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    from config.config import Config
    from engines.sync_engine import SyncEngine
    from engines.force_sync_engine import ForceSyncEngine


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


def main():
    config = Config()
    
    # Проверка конфигурации
    if not config.validate():
        missing_vars = config.get_missing_vars()
        logger.error(f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Определяем тип синхронизации
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        sync_engine = ForceSyncEngine(config)
        sync_engine.force_sync_all()
    else:
        sync_engine = SyncEngine(config)
        sync_engine.sync()


if __name__ == "__main__":
    main()