"""Adaptador LLM/FAQ/flow para reservas médicas.

Flujo: seguridad -> FAQ -> Google AI Studio (Gemini) -> flow de reserva.
"""
import os
from typing import Dict, Generator
from dotenv import load_dotenv
import requests
import json
import reservas_flow as appointment_flow
import reservas_sequrity as sequrity
import reservas_database as database
from reservas_faq import FAQMatcher
from reservas_memory import MemoryManager

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")

# Contexto del sistema para el LLM
SYSTEM_CONTEXT = """Eres un asistente virtual amable y profesional para un sistema de reservas médicas de una clínica.

Tu rol es:
- Ayudar a los pacientes a agendar citas médicas
- Responder preguntas sobre horarios, especialidades, precios y servicios
- Ser empático y profesional en todo momento
- Dar respuestas concisas pero completas

Información de la clínica:
- Horario: Lunes a Viernes 8:00 AM - 8:00 PM, Sábados 8:00 AM - 2:00 PM
- Especialidades: Medicina General, Pediatría, Cardiología, Dermatología, Ginecología, Traumatología, Oftalmología, Neurología, Psicología, Nutrición
- Precios: Consulta General S/.50, Especialista S/.80-120
- Métodos de pago: Efectivo, tarjeta, Yape/Plin, seguros médicos
- Teléfono: (01) 555-1234

Si el paciente quiere agendar una cita, indícale que escriba "quiero una cita" para iniciar el proceso guiado.
Responde siempre en español y de forma amigable."""


class ChatbotService:
    def __init__(self):
        self.faq = FAQMatcher(threshold=0.65)
        self.memory = MemoryManager(k=8)

    def _build_prompt(self, user_message: str, context: str = "") -> str:
        """Construye el prompt completo para Gemini."""
        full_prompt = f"{SYSTEM_CONTEXT}\n\n"
        if context:
            full_prompt += f"Contexto de la conversación:\n{context}\n\n"
        full_prompt += f"Mensaje del paciente: {user_message}\n\nResponde de forma útil y concisa:"
        return full_prompt

    def _call_gemini(self, user_message: str, context: str = "") -> str:
        """Llama a Google AI Studio (Gemini) API."""
        if not GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY no configurada")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GOOGLE_MODEL}:generateContent?key={GOOGLE_API_KEY}"
        full_prompt = self._build_prompt(user_message, context)
        
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024,
                "topP": 0.95,
                "topK": 40
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            
            if "candidates" in data and data["candidates"]:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]
            
            return "Lo siento, no pude generar una respuesta. ¿Puedo ayudarte con algo más?"
        except Exception as e:
            print(f"Error llamando a Gemini: {e}")
            raise

    def _call_gemini_stream(self, user_message: str, context: str = "") -> Generator[str, None, None]:
        """Llama a Google AI Studio (Gemini) API con streaming."""
        if not GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY no configurada")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GOOGLE_MODEL}:streamGenerateContent?alt=sse&key={GOOGLE_API_KEY}"
        full_prompt = self._build_prompt(user_message, context)
        
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024,
                "topP": 0.95,
                "topK": 40
            }
        }

        try:
            with requests.post(url, json=payload, timeout=120, stream=True) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        line_text = line.decode('utf-8')
                        if line_text.startswith('data: '):
                            json_str = line_text[6:]
                            try:
                                data = json.loads(json_str)
                                if "candidates" in data and data["candidates"]:
                                    candidate = data["candidates"][0]
                                    if "content" in candidate and "parts" in candidate["content"]:
                                        parts = candidate["content"]["parts"]
                                        if parts and "text" in parts[0]:
                                            yield parts[0]["text"]
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            print(f"Error en streaming de Gemini: {e}")
            yield "Lo siento, hubo un error. ¿Puedo ayudarte con algo más?"

    def handle_chat_stream(self, user_id: str, message: str) -> Generator[Dict, None, None]:
        """Maneja el chat con streaming para respuestas en tiempo real."""
        
        # 1. Verificación de seguridad
        for pal in sequrity.palabras_in:
            if pal in message.lower():
                yield {"type": "complete", "text": sequrity.responses[0], "reasoning": "Seguridad"}
                return

        # 2. Buscar en FAQ
        faq_answer, sim = self.faq.find_answer(message)
        if faq_answer:
            self.memory.add_user_message(user_id, message)
            self.memory.add_ai_message(user_id, faq_answer)
            database.add_message_to_chat(user_id, "user", message)
            database.add_message_to_chat(user_id, "assistant", faq_answer)
            yield {"type": "complete", "text": faq_answer, "reasoning": f"FAQ ({sim:.2f})"}
            return

        # 3. Verificar si el usuario está en un flujo de reserva
        user = database.get_user(user_id)
        user_state = user.get("state", "idle") if user else "idle"
        
        if user_state != "idle":
            result = appointment_flow.process_message(user_id, message)
            reply = result.get("reply", "")
            self.memory.add_user_message(user_id, message)
            self.memory.add_ai_message(user_id, reply)
            database.add_message_to_chat(user_id, "user", message)
            database.add_message_to_chat(user_id, "assistant", reply)
            yield {"type": "complete", "text": reply, "reasoning": f"Flow ({user_state})"}
            return

        # 4. Detectar intención de reservar
        booking_keywords = ["cita", "reserv", "agend", "turno", "consulta", "doctor", "médico"]
        if any(kw in message.lower() for kw in booking_keywords):
            result = appointment_flow.process_message(user_id, message)
            reply = result.get("reply", "")
            self.memory.add_user_message(user_id, message)
            self.memory.add_ai_message(user_id, reply)
            database.add_message_to_chat(user_id, "user", message)
            database.add_message_to_chat(user_id, "assistant", reply)
            yield {"type": "complete", "text": reply, "reasoning": "Intención reserva"}
            return

        # 5. Usar Gemini con streaming
        if GOOGLE_API_KEY:
            try:
                recent = self.memory.get_recent_messages(user_id, k=4)
                context = "\n".join([f"{m['role']}: {m['content']}" for m in recent])
                
                full_text = ""
                for chunk in self._call_gemini_stream(message, context):
                    full_text += chunk
                    yield {"type": "chunk", "text": chunk}
                
                # Guardar mensaje completo
                self.memory.add_user_message(user_id, message)
                self.memory.add_ai_message(user_id, full_text)
                database.add_message_to_chat(user_id, "user", message)
                database.add_message_to_chat(user_id, "assistant", full_text)
                yield {"type": "done", "reasoning": "Gemini"}
                return
            except Exception as e:
                print(f"Gemini streaming falló: {e}")

        # 6. Fallback
        result = appointment_flow.process_message(user_id, message)
        reply = result.get("reply", "")
        self.memory.add_user_message(user_id, message)
        self.memory.add_ai_message(user_id, reply)
        database.add_message_to_chat(user_id, "user", message)
        database.add_message_to_chat(user_id, "assistant", reply)
        yield {"type": "complete", "text": reply, "reasoning": "Fallback"}

    def handle_chat(self, user_id: str, message: str) -> Dict:
        # 1. Verificación de seguridad
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

        # 2. Verificar si el usuario está en un flujo de reserva activo
        user = database.get_user(user_id)
        user_state = user.get("state", "idle") if user else "idle"
        
        if user_state != "idle":
            result = appointment_flow.process_message(user_id, message)
            reply = result.get("reply", "")
            self.memory.add_user_message(user_id, message)
            self.memory.add_ai_message(user_id, reply)
            database.add_message_to_chat(user_id, "user", message)
            database.add_message_to_chat(user_id, "assistant", reply)
            return {
                "reasoning": f"Flujo de reserva activo (estado: {user_state})",
                "to_user": reply,
                "data": None,
                "action": None,
                "is_faq_response": False,
            }

        # 3. Detectar intención de reservar (ANTES del FAQ y Gemini)
        booking_keywords = ["cita", "reserv", "agend", "turno", "agendar", "reservar", "necesito ver"]
        if any(kw in message.lower() for kw in booking_keywords):
            result = appointment_flow.process_message(user_id, message)
            reply = result.get("reply", "")
            self.memory.add_user_message(user_id, message)
            self.memory.add_ai_message(user_id, reply)
            database.add_message_to_chat(user_id, "user", message)
            database.add_message_to_chat(user_id, "assistant", reply)
            return {
                "reasoning": "Intención de reserva detectada",
                "to_user": reply,
                "data": None,
                "action": None,
                "is_faq_response": False,
            }

        # 4. Buscar en FAQ
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

        # 5. Usar Gemini para respuestas generales
        if GOOGLE_API_KEY:
            try:
                # Obtener contexto de conversación
                recent = self.memory.get_recent_messages(user_id, k=4)
                context = "\n".join([f"{m['role']}: {m['content']}" for m in recent])
                
                text = self._call_gemini(message, context)
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
            except Exception as e:
                print(f"Gemini falló, usando flow: {e}")

        # 6. Fallback al flujo de reserva
        result = appointment_flow.process_message(user_id, message)
        reply = result.get("reply", "")
        self.memory.add_user_message(user_id, message)
        self.memory.add_ai_message(user_id, reply)
        database.add_message_to_chat(user_id, "user", message)
        database.add_message_to_chat(user_id, "assistant", reply)
        return {
            "reasoning": "Respuesta del flow de reserva",
            "to_user": reply,
            "data": None,
            "action": None,
            "is_faq_response": False,
        }
