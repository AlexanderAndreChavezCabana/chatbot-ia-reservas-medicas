"""Adaptador LLM/FAQ/flow para reservas (usa reservas_* módulos).

Flujo: seguridad -> FAQ -> AiStudio (si está habilitado) -> flow de reserva.
"""
import os
from typing import Dict
import requests
import reservas_flow as appointment_flow
import reservas_sequrity as sequrity
import reservas_database as database
from reservas_faq import FAQMatcher
from reservas_memory import MemoryManager

USE_AISTUDIO = os.getenv("USE_AISTUDIO", "false").lower() in ("1", "true", "yes")
AISTUDIO_API_KEY = os.getenv("AISTUDIO_API_KEY")
AISTUDIO_MODEL = os.getenv("AISTUDIO_MODEL")
AISTUDIO_BASE_URL = os.getenv("AISTUDIO_BASE_URL", "https://api.aistudio.example")


class ChatbotService:
    def __init__(self):
        self.faq = FAQMatcher(threshold=0.85)
        self.memory = MemoryManager(k=8)

    def _call_aistudio(self, user_message: str) -> str:
        if not AISTUDIO_API_KEY or not AISTUDIO_MODEL:
            raise RuntimeError("AiStudio credentials or model not configured")

        url = AISTUDIO_BASE_URL.rstrip("/") + "/v1/generate"
        headers = {"Authorization": f"Bearer {AISTUDIO_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": AISTUDIO_MODEL, "input": user_message}

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, dict):
                for key in ("output", "text", "response", "result", "content"):
                    if key in data and isinstance(data[key], str):
                        return data[key]

                if "responses" in data and isinstance(data["responses"], list) and data["responses"]:
                    first = data["responses"][0]
                    if isinstance(first, dict) and "content" in first:
                        return first["content"]
                    if isinstance(first, str):
                        return first

            return resp.text
        except Exception as e:
            print("Error calling AiStudio endpoint:", e)
            raise

    def handle_chat(self, user_id: str, message: str) -> Dict:
        for pal in sequrity.palabras_in:
            if pal in message.lower():
                return {
                    "reasoning": f"Palabra prohibida detectada: {pal}",
                    "to_user": sequrity.responses[0],
                    "data": None,
                    "action": None,
                    "is_faq_response": True,
                    "faq_similarity": 0.0,
                }

        faq_answer, sim = self.faq.find_answer(message)
        if faq_answer:
            self.memory.add_user_message(user_id, message)
            self.memory.add_ai_message(user_id, faq_answer)
            database.add_message_to_chat(user_id, "user", message)
            database.add_message_to_chat(user_id, "assistant", faq_answer)
            return {
                "reasoning": f"Respuesta desde FAQ (similitud: {sim:.2f})",
                "to_user": faq_answer,
                "data": None,
                "action": None,
                "is_faq_response": True,
                "faq_similarity": sim,
            }

        if USE_AISTUDIO:
            try:
                text = self._call_aistudio(message)
                self.memory.add_user_message(user_id, message)
                self.memory.add_ai_message(user_id, text)
                database.add_message_to_chat(user_id, "user", message)
                database.add_message_to_chat(user_id, "assistant", text)
                return {
                    "reasoning": "Respuesta generada por AiStudio",
                    "to_user": text,
                    "data": None,
                    "action": None,
                    "is_faq_response": False,
                }
            except Exception:
                # En caso de fallo con AiStudio, caemos al flow local
                pass

        result = appointment_flow.process_message(user_id, message)
        self.memory.add_user_message(user_id, message)
        self.memory.add_ai_message(user_id, result.get("reply", ""))
        database.add_message_to_chat(user_id, "user", message)
        database.add_message_to_chat(user_id, "assistant", result.get("reply", ""))
        return {
            "reasoning": "Generado por regla/flow",
            "to_user": result.get("reply", ""),
            "data": None,
            "action": None,
        }
