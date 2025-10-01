import msal
import requests
import os
import json
from dotenv import load_dotenv
import logging

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

load_dotenv()

# === Настройки ===
MS_CLIENT_ID = os.getenv("MS_CLIENT_ID")
AUTHORITY = "https://login.microsoftonline.com/consumers"
SCOPE = ["Tasks.ReadWrite"]
CACHE_FILE = "token_cache.bin"

KAITEN_TOKEN = os.getenv("KAITEN_API_TOKEN")
KAITEN_DOMAIN = os.getenv("KAITEN_DOMAIN")
KAITEN_SPACE_ID = os.getenv("KAITEN_SPACE_ID")
KAITEN_BOARD_ID = int(os.getenv("KAITEN_BOARD_ID"))
KAITEN_COLUMN_ID = int(os.getenv("KAITEN_COLUMN_ID"))
KAITEN_API_BASE = f"https://{KAITEN_DOMAIN}/api/latest"

MAPPING_FILE = "sync_mapping.json"
SYNC_LIST_NAME = "Задачи"

# === Вспомогательные функции ===
def load_cache():
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache.deserialize(f.read())
    return cache

def save_cache(cache):
    if cache.has_state_changed:
        with open(CACHE_FILE, "w") as f:
            f.write(cache.serialize())

def load_mapping():
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_mapping(mapping):
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

def compute_todo_hash(task):
    desc = (task.get("body") or {}).get("content") or ""
    due = task.get("dueDateTime", {}).get("dateTime")
    due_str = due.split("T")[0] if due else ""
    return f"{task['title']}|{desc}|{due_str}|{task['status']}"

def compute_kaiten_hash(card):
    desc = card.get("description") or ""
    due_raw = card.get("due_date") or ""
    # Нормализуем дату из Kaiten к формату YYYY-MM-DD
    if due_raw and "T" in due_raw:
        due = due_raw.split("T")[0]
    else:
        due = due_raw
    status = "completed" if card.get("state") == 2 else "notStarted"
    return f"{card['title']}|{desc}|{due}|{status}"

def todo_date_to_kaiten_date(todo_due):
    if not todo_due:
        return None
    return todo_due.split("T")[0]

def kaiten_date_to_todo_date(kaiten_due):
    if not kaiten_due:
        return None
    return f"{kaiten_due}T10:00:00.0000000"

# === Microsoft Auth ===
def get_ms_access_token():
    cache = load_cache()
    app = msal.PublicClientApplication(MS_CLIENT_ID, authority=AUTHORITY, token_cache=cache)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPE, account=accounts[0])
        if result:
            save_cache(cache)
            return result["access_token"]
    logger.info("Требуется авторизация в Microsoft...")
    flow = app.initiate_device_flow(scopes=SCOPE)
    logger.info(f"Перейдите по ссылке и введите код:\n{flow['message']}")
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" in result:
        save_cache(cache)
        return result["access_token"]
    else:
        raise Exception(f"Ошибка авторизации: {result.get('error_description')}")

# === Microsoft To Do ===
def get_todo_list_id(access_token):
    resp = requests.get("https://graph.microsoft.com/v1.0/me/todo/lists", headers={"Authorization": f"Bearer {access_token}"})
    resp.raise_for_status()
    for lst in resp.json()["value"]:
        if lst["displayName"] == SYNC_LIST_NAME:
            return lst["id"]
    raise Exception(f"Список '{SYNC_LIST_NAME}' не найден")

def get_active_tasks_from_todo(access_token, list_id):
    resp = requests.get(f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks", headers={"Authorization": f"Bearer {access_token}"})
    resp.raise_for_status()
    tasks = resp.json()["value"]
    return {t["id"]: t for t in tasks if t["status"] in ("notStarted", "inProgress", "completed")}

def update_todo_task(access_token, list_id, task_id, title=None, description=None, due_date=None, status=None):
    url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks/{task_id}"
    payload = {}
    changes = []
    if title is not None:
        payload["title"] = title
        changes.append(f"title='{title}'")
    if description is not None:
        payload["body"] = {"content": description or "", "contentType": "text"}
        changes.append(f"description='{(description or '')[:30]}...'")
    if due_date is not None:
        if due_date:
            payload["dueDateTime"] = {"dateTime": due_date, "timeZone": "UTC"}
        else:
            payload["dueDateTime"] = None
        changes.append(f"due_date={due_date}")
    if status is not None:
        payload["status"] = status
        changes.append(f"status={status}")
    
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    resp = requests.patch(url, json=payload, headers=headers)
    if resp.status_code == 200:
        logger.info(f"✅ To Do ← Kaiten | Обновлена задача '{task_id}': {', '.join(changes)}")
        return True
    else:
        logger.error(f"❌ Не удалось обновить задачу в To Do: {resp.status_code} {resp.text[:200]}")
        return False

# === Kaiten ===
def get_kaiten_cards():
    url = f"{KAITEN_API_BASE}/spaces/{KAITEN_SPACE_ID}/boards/{KAITEN_BOARD_ID}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {KAITEN_TOKEN}",
        "User-Agent": "PostmanRuntime/7.32.3"
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    cards = resp.json().get("cards", [])
    return {c["id"]: c for c in cards if c.get("column_id") == KAITEN_COLUMN_ID}

def create_kaiten_card(title, description, due_date):
    payload = {
        "title": title,
        "description": description or "",
        "board_id": KAITEN_BOARD_ID,
        "column_id": KAITEN_COLUMN_ID,
        "due_date": due_date,
        "priority": 1
    }
    headers = {
        "Authorization": f"Bearer {KAITEN_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "PostmanRuntime/7.32.3"
    }
    resp = requests.post(f"{KAITEN_API_BASE}/cards", json=payload, headers=headers)
    if resp.status_code == 200:
        card_id = resp.json()["id"]
        logger.info(f"✅ Kaiten ← To Do | Создана карточка: '{title}' (ID: {card_id})")
        return card_id
    else:
        logger.error(f"❌ Не удалось создать карточку в Kaiten: {resp.status_code}")
        return None

def update_kaiten_card(card_id, title=None, description=None, due_date=None):
    payload = {}
    changes = []
    if title is not None:
        payload["title"] = title
        changes.append(f"title='{title}'")
    if description is not None:
        payload["description"] = description or ""
        changes.append(f"description='{(description or '')[:30]}...'")
    if due_date is not None:
        payload["due_date"] = due_date
        changes.append(f"due_date={due_date}")
    
    headers = {
        "Authorization": f"Bearer {KAITEN_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "PostmanRuntime/7.32.3"
    }
    resp = requests.patch(f"{KAITEN_API_BASE}/cards/{card_id}", json=payload, headers=headers)
    if resp.status_code == 200:
        logger.info(f"✅ Kaiten ← To Do | Обновлена карточка {card_id}: {', '.join(changes)}")
        return True
    else:
        logger.error(f"❌ Не удалось обновить карточку {card_id} в Kaiten: {resp.status_code}")
        return False

def delete_kaiten_card(card_id):
    headers = {"Authorization": f"Bearer {KAITEN_TOKEN}", "User-Agent": "PostmanRuntime/7.32.3"}
    resp = requests.delete(f"{KAITEN_API_BASE}/cards/{card_id}", headers=headers)
    if resp.status_code == 204:
        logger.info(f"🗑️ Kaiten ← To Do | Удалена карточка {card_id}")
        return True
    else:
        logger.error(f"❌ Не удалось удалить карточку {card_id}")
        return False

# === Основная синхронизация ===
def sync_todo_with_kaiten():
    logger.info("🔄 Запуск синхронизации To Do ↔ Kaiten")
    try:
        token = get_ms_access_token()
        list_id = get_todo_list_id(token)
        todo_tasks = get_active_tasks_from_todo(token, list_id)
        kaiten_cards = get_kaiten_cards()
        mapping = load_mapping()

        # Очистка маппинга от удалённых карточек
        new_mapping = {}
        for todo_id, meta in mapping.items():
            kaiten_id = meta["kaiten_card_id"]
            if kaiten_id in kaiten_cards:
                new_mapping[todo_id] = meta
            else:
                logger.info(f"ℹ️ Карточка {kaiten_id} удалена вручную — удаляем из маппинга")
        mapping = new_mapping

        # Синхронизация существующих пар
        for todo_id, meta in list(mapping.items()):
            kaiten_id = meta["kaiten_card_id"]
            if todo_id not in todo_tasks or kaiten_id not in kaiten_cards:
                continue

            todo = todo_tasks[todo_id]
            card = kaiten_cards[kaiten_id]

            current_todo_hash = compute_todo_hash(todo)
            current_kaiten_hash = compute_kaiten_hash(card)

            saved_todo_hash = meta.get("todo_hash", "")
            saved_kaiten_hash = meta.get("kaiten_hash", "")

            # To Do изменился
            if current_todo_hash != saved_todo_hash:
                t_desc = (todo.get("body") or {}).get("content") or ""
                t_due = todo_date_to_kaiten_date(todo.get("dueDateTime", {}).get("dateTime"))
                if update_kaiten_card(kaiten_id, title=todo["title"], description=t_desc, due_date=t_due):
                    # Сразу обновляем хэш в маппинге, чтобы избежать гонки
                    updated_card = {
                        "title": todo["title"],
                        "description": t_desc,
                        "due_date": t_due or "",
                        "state": 1  # notStarted
                    }
                    meta["kaiten_hash"] = compute_kaiten_hash(updated_card)
                    meta["todo_hash"] = current_todo_hash

            # Kaiten изменился
            elif current_kaiten_hash != saved_kaiten_hash:
                k_desc = card.get("description") or ""
                k_due = card.get("due_date")
                k_status = "completed" if card.get("state") == 2 else "notStarted"
                update_todo_task(
                    token, list_id, todo_id,
                    title=card["title"],
                    description=k_desc,
                    due_date=kaiten_date_to_todo_date(k_due) if k_due else None,
                    status=k_status
                )
                meta["kaiten_hash"] = current_kaiten_hash
                meta["todo_hash"] = current_todo_hash

            mapping[todo_id] = meta

        # Создание новых задач
        for todo_id, todo in todo_tasks.items():
            if todo_id in mapping:
                continue
            if todo["status"] == "completed":
                continue
            t_desc = (todo.get("body") or {}).get("content") or ""
            t_due = todo_date_to_kaiten_date(todo.get("dueDateTime", {}).get("dateTime"))
            card_id = create_kaiten_card(title=todo["title"], description=t_desc, due_date=t_due)
            if card_id:
                # Эмулируем состояние карточки для корректного хэша
                fake_card = {
                    "title": todo["title"],
                    "description": t_desc,
                    "due_date": t_due or "",
                    "state": 1
                }
                kaiten_hash = compute_kaiten_hash(fake_card)
                todo_hash = compute_todo_hash(todo)
                mapping[todo_id] = {
                    "kaiten_card_id": card_id,
                    "todo_hash": todo_hash,
                    "kaiten_hash": kaiten_hash
                }

        # Удаление задач
        for todo_id, meta in list(mapping.items()):
            if todo_id not in todo_tasks:
                if delete_kaiten_card(meta["kaiten_card_id"]):
                    del mapping[todo_id]

        save_mapping(mapping)
        logger.info("✅ Синхронизация завершена успешно")
    except Exception as e:
        logger.exception(f"❌ Критическая ошибка: {e}")

# === Запуск ===
if __name__ == "__main__":
    sync_todo_with_kaiten()