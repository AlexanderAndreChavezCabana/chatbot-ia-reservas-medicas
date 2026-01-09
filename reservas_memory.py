"""
Simple memory manager for conversational context (reservas).
"""
from typing import List, Dict
import reservas_database as database

DEFAULT_K = 8


class MemoryManager:
    def __init__(self, k: int = DEFAULT_K):
        self.k = k

    def add_user_message(self, user_id: str, message: str):
        database.add_message_to_chat(user_id, "user", message)

    def add_ai_message(self, user_id: str, message: str):
        database.add_message_to_chat(user_id, "assistant", message)

    def get_recent_messages(self, user_id: str, k: int = None) -> List[Dict]:
        if k is None:
            k = self.k
        messages = database.get_chat_messages(user_id)
        return messages[-k:] if len(messages) > k else messages

    def clear_memory(self, user_id: str):
        chats = database.load_json(database.CHATS_FILE)
        if user_id in chats:
            chats[user_id]["messages"] = []
            database.save_json(database.CHATS_FILE, chats)

    def get_summary(self, user_id: str) -> str:
        messages = database.get_chat_messages(user_id)
        if not messages:
            return ""
        older = messages[:-self.k] if len(messages) > self.k else []
        assistant_texts = [m["content"] for m in older if m.get("role") == "assistant"]
        return "\n".join(assistant_texts)
