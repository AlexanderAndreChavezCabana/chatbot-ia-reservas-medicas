"""LLM service with optional Google (Gemini) integration.

This module supports three modes:
 - If `USE_GOOGLE_GEMINI` env var is set to `true`, it will attempt to call
   Vertex AI (Gemini) using the Google Cloud SDK.
 - Otherwise it falls back to a lightweight rule-based flow in
   `appointment_flow` (already implemented).

Setup instructions:
 - Install requirements: `pip install -r requirements.txt`
 - Set Google credentials and config if using Gemini:
     - `GOOGLE_APPLICATION_CREDENTIALS` -> path to service account JSON
     - `GCP_PROJECT` -> GCP project id
     - `GCP_LOCATION` -> region (e.g. `us-central1`)
     - `GEMINI_MODEL` -> model id (default: `gemini-2.5-pro`)
     - `USE_GOOGLE_GEMINI=true` to enable

Note: this is a best-effort adapter. API usage may require additional
permissions and updated client libraries depending on Google SDK versions.
"""

import os
from typing import Dict
import appointment_flow
import sequrity
import database
from faq_system import FAQMatcher
from memory_manager import MemoryManager

USE_GOOGLE = os.getenv("USE_GOOGLE_GEMINI", "false").lower() in ("1", "true", "yes")
GCP_PROJECT = os.getenv("GCP_PROJECT")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")


class ChatbotService:
    def __init__(self):
        self.google_available = False
        self.faq = FAQMatcher(threshold=0.85)
        self.memory = MemoryManager(k=8)

        if USE_GOOGLE:
            try:
                from google.cloud import aiplatform
                if GCP_PROJECT:
                    aiplatform.init(project=GCP_PROJECT, location=GCP_LOCATION)
                self.aiplatform = aiplatform
                self.google_available = True
            except Exception as e:
                print("Google Vertex AI SDK not available or failed to init:", e)
                self.google_available = False

    def _call_gemini(self, user_message: str) -> str:
        if not self.google_available:
            raise RuntimeError("Google Vertex AI SDK not initialized")

        try:
            from google.cloud.aiplatform import gapic as aiplatform_gapic

            client = aiplatform_gapic.PredictionServiceClient()
            name = f"projects/{GCP_PROJECT}/locations/{GCP_LOCATION}/models/{GEMINI_MODEL}"
            instance = {"content": user_message}
            response = client.predict(endpoint=name, instances=[instance])
            predictions = getattr(response, "predictions", None) or []
            if predictions:
                first = predictions[0]
                if isinstance(first, dict):
                    for k in ("content", "text", "output"):
                        if k in first:
                            return first[k]
                    return str(first)
                return str(first)

            return "Lo siento, no obtuve respuesta del modelo."

        except Exception as e:
            print("Error calling Gemini/Vertex AI:", e)
            raise

    def handle_chat(self, user_id: str, message: str) -> Dict:
        # Security check
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

        # FAQ check
        faq_answer, sim = self.faq.find_answer(message)
        if faq_answer:
            # Save to memory and chats
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

        # Try Gemini if enabled
        if USE_GOOGLE and self.google_available:
            try:
                text = self._call_gemini(message)
                self.memory.add_user_message(user_id, message)
                self.memory.add_ai_message(user_id, text)
                database.add_message_to_chat(user_id, "user", message)
                database.add_message_to_chat(user_id, "assistant", text)
                return {
                    "reasoning": "Respuesta generada por Gemini",
                    "to_user": text,
                    "data": None,
                    "action": None,
                    "is_faq_response": False,
                }
            except Exception:
                pass

        # Fallback to appointment flow
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
