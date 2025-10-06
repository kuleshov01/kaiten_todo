# Документация по использованию проекта синхронизации Microsoft To Do и Kaiten

## Установка

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Создайте файл `.env` с настройками:
   ```env
   # Microsoft To Do
   MS_CLIENT_ID=your_client_id_here
   
   # Kaiten
   KAITEN_API_TOKEN=your_api_token_here
   KAITEN_DOMAIN=your_domain.kaiten.ru
   KAITEN_SPACE_ID=your_space_id
   KAITEN_BOARD_ID=your_board_id
   KAITEN_COLUMN_ID=your_column_id
   ```

## Настройка

1. Для получения `MS_CLIENT_ID`:
   - Зарегистрируйте приложение в Azure Active Directory
   - Настройте разрешения для Microsoft Graph API
   - Укажите `https://login.microsoftonline.com/consumers/oauth2/v2.0/token` как разрешенный URI ответа

2. Для получения данных Kaiten:
   - Получите API-токен в настройках вашего аккаунта Kaiten
   - Найдите ID пространства, доски и колонки через веб-интерфейс или API

## Использование

### Обычная синхронизация
```bash
python -m src.main
```

### Принудительная синхронизация (обновляет все задачи)
```bash
python -m src.main --force
```

## Конфигурация

Основные параметры синхронизации можно настроить в файле `src/config/config.py`:
- `SYNC_LIST_NAME` - название списка задач в Microsoft To Do для синхронизации
- `MAPPING_FILE` - файл для хранения сопоставлений задач между системами

## Логирование

Логи синхронизации сохраняются в файл `sync.log` в корне проекта.