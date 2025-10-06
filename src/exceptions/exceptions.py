#!/usr/bin/env python3
"""
Модуль исключений для приложения синхронизации Microsoft To Do и Kaiten
"""


class SyncError(Exception):
    """Базовое исключение для ошибок синхронизации"""
    pass


class MicrosoftTodoError(SyncError):
    """Исключение для ошибок Microsoft To Do API"""
    pass


class KaitenError(SyncError):
    """Исключение для ошибок Kaiten API"""
    pass