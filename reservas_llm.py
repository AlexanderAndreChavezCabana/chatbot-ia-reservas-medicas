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
SYSTEM_CONTEXT = """Eres "MediBot", el asistente virtual de la Clínica San Rafael. Tu personalidad es cálida, empática y profesional.

🏥 INFORMACIÓN DE LA CLÍNICA:
- Nombre: Clínica San Rafael
- Dirección: Av. Javier Prado 1234, San Isidro, Lima
- Teléfono: (01) 555-1234 | WhatsApp: 987-654-321
- Horario: Lunes a Viernes 8:00 AM - 8:00 PM, Sábados 8:00 AM - 2:00 PM
- Domingos y feriados: Solo emergencias

👨‍⚕️ ESPECIALIDADES Y PRECIOS:
- Medicina General: S/.50
- Pediatría: S/.70
- Cardiología: S/.100
- Dermatología: S/.80
- Ginecología: S/.90
- Traumatología: S/.100
- Oftalmología: S/.80
- Neurología: S/.120
- Psicología: S/.80
- Nutrición: S/.60

💳 MÉTODOS DE PAGO:
- Efectivo, Visa, Mastercard, American Express
- Yape, Plin, transferencia bancaria
- Seguros: Rímac, Pacífico, Mapfre, La Positiva, EPS

📋 INSTRUCCIONES:
1. Responde de forma natural y conversacional, como un humano amigable
2. Varía tus saludos y despedidas, no uses siempre las mismas frases
3. Si preguntan por agendar cita, diles: "Escribe 'quiero una cita' y te guío paso a paso 😊"
4. Usa emojis con moderación para hacer la conversación más amigable
5. Si no sabes algo, sé honesto y ofrece alternativas
6. Personaliza las respuestas según el contexto de la conversación
7. Mantén respuestas cortas (2-4 oraciones) a menos que se requiera más detalle

🚫 EVITA:
- Respuestas robóticas o repetitivas
- Inventar información médica
- Dar diagnósticos o recomendaciones médicas específicas
- Usar siempre la misma estructura de respuesta"""


class ChatbotService:
    def __init__(self):
        self.faq = FAQMatcher(threshold=0.65)
        self.memory = MemoryManager(k=8)

    def _build_prompt(self, user_message: str, context: str = "", user_name: str = "") -> str:
        """Construye el prompt completo para Gemini."""
        import random
        
        # Variaciones para hacer el prompt más dinámico
        response_styles = [
            "Responde de manera cálida y natural:",
            "Da una respuesta amigable y útil:",
            "Responde como un asistente empático:",
            "Contesta de forma profesional pero cercana:",
        ]
        
        full_prompt = f"{SYSTEM_CONTEXT}\n\n"
        
        if user_name:
            full_prompt += f"El paciente se llama: {user_name}\n\n"
        
        if context:
            full_prompt += f"📝 Historial reciente de la conversación:\n{context}\n\n"
        
        full_prompt += f"💬 Mensaje del paciente: {user_message}\n\n"
        full_prompt += random.choice(response_styles)
        
        return full_prompt

    def _call_gemini(self, user_message: str, context: str = "", user_name: str = "") -> str:
        """Llama a Google AI Studio (Gemini) API."""
        if not GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY no configurada")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GOOGLE_MODEL}:generateContent?key={GOOGLE_API_KEY}"
        full_prompt = self._build_prompt(user_message, context, user_name)
        
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0.85,  # Más variedad en respuestas
                "maxOutputTokens": 1024,
                "topP": 0.92,
                "topK": 50  # Más opciones de tokens
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

    def _call_gemini_stream(self, user_message: str, context: str = "", user_name: str = "") -> Generator[str, None, None]:
        """Llama a Google AI Studio (Gemini) API con streaming."""
        if not GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY no configurada")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GOOGLE_MODEL}:streamGenerateContent?alt=sse&key={GOOGLE_API_KEY}"
        full_prompt = self._build_prompt(user_message, context, user_name)
        
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0.85,
                "maxOutputTokens": 1024,
                "topP": 0.92,
                "topK": 50
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
                user_name = user.get("name", "") if user else ""
                
                full_text = ""
                for chunk in self._call_gemini_stream(message, context, user_name):
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

        # 4. Preguntas informativas → LLM genera respuesta variada
        info_keywords = ["horario", "hora", "precio", "costo", "cuanto", "cuánto", "pago", "tarjeta", 
                        "efectivo", "seguro", "especialidad", "doctor", "médico", "yape", "plin",
                        "abren", "cierran", "atienden", "cobran", "tarifa"]
        is_info_question = any(kw in message.lower() for kw in info_keywords)
        
        if is_info_question and GOOGLE_API_KEY:
            try:
                user_name = user.get("name", "") if user else ""
                text = self._call_gemini(message, "", user_name)
                self.memory.add_user_message(user_id, message)
                self.memory.add_ai_message(user_id, text)
                database.add_message_to_chat(user_id, "user", message)
                database.add_message_to_chat(user_id, "assistant", text)
                return {
                    "reasoning": "Pregunta informativa → Gemini",
                    "to_user": text,
                    "data": None,
                    "action": None,
                    "is_faq_response": False,
                }
            except Exception as e:
                print(f"Gemini falló para pregunta informativa: {e}")
                # Si falla, usar FAQ como fallback

        # 5. Buscar en FAQ (fallback si LLM no está disponible)
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

        # 6. Usar Gemini para respuestas generales
        if GOOGLE_API_KEY:
            try:
                # Obtener contexto de conversación y nombre del usuario
                recent = self.memory.get_recent_messages(user_id, k=4)
                context = "\n".join([f"{m['role']}: {m['content']}" for m in recent])
                user_name = user.get("name", "") if user else ""
                
                text = self._call_gemini(message, context, user_name)
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

        # 7. Fallback al flujo de reserva
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
