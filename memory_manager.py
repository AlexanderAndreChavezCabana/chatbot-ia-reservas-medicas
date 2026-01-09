"""
Simple memory manager for conversational context.
Stores recent messages per user in `data/chats.json` and returns last k messages.
"""
from typing import List, Dict
from datetime import datetime
import database

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
        # Reset chat messages for user
        chats = database.load_json(database.CHATS_FILE)
        if user_id in chats:
            chats[user_id]["messages"] = []
            database.save_json(database.CHATS_FILE, chats)

    def get_summary(self, user_id: str) -> str:
        # Very simple summary: join assistant utterances older than recent window
        messages = database.get_chat_messages(user_id)
        if not messages:
            return ""
        # Take all messages except the last k and concatenate assistant replies
        older = messages[:-self.k] if len(messages) > self.k else []
        assistant_texts = [m["content"] for m in older if m.get("role") == "assistant"]
        return "\n".join(assistant_texts)
