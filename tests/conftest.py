"""Общие настройки pytest для тестов проекта."""

from __future__ import annotations

import sys
from pathlib import Path

# Добавляем корень проекта в sys.path, чтобы можно было импортировать пакет src
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
