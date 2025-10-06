"""Модуль с определением исключений для приложения синхронизации"""

class SyncError(Exception):
    """Базовое исключение для ошибок синхронизации"""
    pass

class MicrosoftTodoError(SyncError):
    """Исключение для ошибок Microsoft To Do API"""
    pass

class KaitenError(SyncError):
    """Исключение для ошибок Kaiten API"""
    pass

class ConfigurationError(SyncError):
    """Исключение для ошибок конфигурации"""
    pass