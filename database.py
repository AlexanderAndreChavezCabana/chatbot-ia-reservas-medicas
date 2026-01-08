import json
import os
from datetime import datetime
from typing import Dict, List, Optional

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
APPTS_FILE = os.path.join(DATA_DIR, "appointments.json")
CHATS_FILE = os.path.join(DATA_DIR, "chats.json")


def ensure_data():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    for p in [USERS_FILE, APPTS_FILE, CHATS_FILE]:
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)


def load_json(path: str) -> Dict:
    ensure_data()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_json(path: str, data: Dict):
    ensure_data()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# Users
def create_user(user_id: str, name: str) -> Dict:
    users = load_json(USERS_FILE)
    if user_id in users:
        raise ValueError("user exists")
    user = {"user_id": user_id, "name": name, "created_at": datetime.now().isoformat(), "state": "idle", "pending": {}}
    users[user_id] = user
    save_json(USERS_FILE, users)
    return user


def get_user(user_id: str) -> Optional[Dict]:
    users = load_json(USERS_FILE)
    return users.get(user_id)


def user_exists(user_id: str) -> bool:
    return get_user(user_id) is not None


def set_user_state(user_id: str, state: str, pending: Dict = None):
    users = load_json(USERS_FILE)
    if user_id not in users:
        raise ValueError("user not found")
    users[user_id]["state"] = state
    users[user_id]["pending"] = pending or {}
    save_json(USERS_FILE, users)


# Chats helpers
def get_chat_messages(user_id: str) -> List[Dict]:
    chats = load_json(CHATS_FILE)
    chat = chats.get(user_id)
    if not chat:
        return []
    return chat.get("messages", [])


def add_message_to_chat(user_id: str, role: str, content: str):
    chats = load_json(CHATS_FILE)
    if user_id not in chats:
        chats[user_id] = {"user_id": user_id, "messages": []}

    message = {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
    chats[user_id]["messages"].append(message)
    save_json(CHATS_FILE, chats)


# Appointments
def save_appointment(appt: Dict) -> str:
    appts = load_json(APPTS_FILE)
    appt_id = f"APPT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    record = {"appointment_id": appt_id, "created_at": datetime.now().isoformat(), **appt}
    appts[appt_id] = record
    save_json(APPTS_FILE, appts)
    return appt_id


def get_user_appointments(user_id: str) -> List[Dict]:
    appts = load_json(APPTS_FILE)
    result = [v for v in appts.values() if v.get("user_id") == user_id]
    return result
