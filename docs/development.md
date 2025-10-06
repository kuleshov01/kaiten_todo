# Документация для разработчиков

## Структура проекта

```
kaiten_todo/
├── src/
│   ├── __init__.py
│   ├── config.py          # Класс конфигурации приложения
│   ├── exceptions.py      # Определение исключений
│   └── utils.py          # Вспомогательные функции
├── docs/
│   └── development.md    # Документация для разработчиков
├── main.py              # Основной файл приложения
├── README.md            # Общая документация
├── requirements.txt     # Зависимости проекта
├── .env.example         # Пример файла переменных окружения
├── .env                 # Файл переменных окружения (не включается в репозиторий)
├── sync_mapping.json    # Файл сопоставлений задач и карточек
├── sync.log            # Лог-файл операций синхронизации
└── token_cache.bin     # Кэш токенов Microsoft
```

## Архитектура

Проект разделен на несколько компонентов:

1. **MicrosoftTodoClient** - класс для работы с Microsoft To Do API
2. **KaitenClient** - класс для работы с Kaiten API
3. **SyncEngine** - движок синхронизации, координирующий работу между двумя системами
4. **Config** - класс для управления конфигурацией приложения
5. **Утилиты** - вспомогательные функции для работы с хэшами и файлами сопоставлений

## Установка и запуск

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Настройка

1. Создайте файл `.env` на основе `.env.example`
2. Заполните все обязательные переменные окружения
3. Проверьте, что у вас есть доступ к соответствующим ресурсам Kaiten и Microsoft

### Запуск

```bash
python main.py
```

## Безопасность

- Не храните токены доступа в открытом виде
- Используйте файл `.env` для хранения конфиденциальных данных
- Регулярно обновляйте токены доступа
- Убедитесь, что у приложения минимально необходимые права доступа

## Обработка ошибок

Проект использует иерархию исключений:

- `SyncError` - базовое исключение для ошибок синхронизации
- `MicrosoftTodoError` - ошибки Microsoft To Do API
- `KaitenError` - ошибки Kaiten API
- `ConfigurationError` - ошибки конфигурации

## Тестирование

Для добавления новых тестов создайте файлы в директории `tests/`:

```python
import unittest
from src.utils import compute_todo_hash

class TestUtils(unittest.TestCase):
    def test_compute_todo_hash(self):
        task = {
            "title": "Test task",
            "body": {"content": "Test description"},
            "dueDateTime": {"dateTime": "2023-12-31T10:00:00.0000000"},
            "status": "notStarted"
        }
        expected_hash = "Test task|Test description|2023-12-31|notStarted"
        self.assertEqual(compute_todo_hash(task), expected_hash)

if __name__ == '__main__':
    unittest.main()
```

## Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функциональности
3. Сделайте изменения
4. Добавьте тесты, если применимо
5. Создайте pull request