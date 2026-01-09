from typing import Dict
import re
from datetime import datetime
import database


BOOK_KEYWORDS = ["cita", "reserv", "agend", "turno", "hora"]


def _looks_like_date(s: str) -> bool:
    try:
        datetime.strptime(s.strip(), "%Y-%m-%d")
        return True
    except:
        return False


def _looks_like_time(s: str) -> bool:
    try:
        datetime.strptime(s.strip(), "%H:%M")
        return True
    except:
        return False


def process_message(user_id: str, message: str) -> Dict:
    """Procesa mensajes del usuario y maneja el flujo de reserva."""
    user = database.get_user(user_id)
    if not user:
        return {"reply": "Usuario no encontrado. Crea tu usuario con POST /users."}

    state = user.get("state", "idle")
    pending = user.get("pending", {}) or {}

    text = message.lower().strip()

    # Cancelar
    if "cancel" in text or "cancelar" in text:
        database.set_user_state(user_id, "idle", {})
        return {"reply": "Reserva cancelada. ¿En qué más puedo ayudarte?"}

    if state == "idle":
        # Detectar intención de reservar
        if any(k in text for k in BOOK_KEYWORDS) or "reservar" in text or "cita" in text:
            database.set_user_state(user_id, "awaiting_specialty", {})
            return {"reply": "Perfecto. ¿Qué especialidad necesitas? Ej: pediatría, cardiología, dermatología."}
        else:
            return {"reply": "Puedo ayudarte a reservar citas médicas. Escribe 'quiero una cita' para comenzar."}

    if state == "awaiting_specialty":
        specialty = message.strip()
        pending["specialty"] = specialty
        database.set_user_state(user_id, "awaiting_date", pending)
        return {"reply": f"Genial. ¿Qué fecha prefieres? Escribe la fecha en formato YYYY-MM-DD."}

    if state == "awaiting_date":
        if _looks_like_date(message):
            pending["date"] = message.strip()
            database.set_user_state(user_id, "awaiting_time", pending)
            return {"reply": "¿A qué hora prefieres la cita? Formato HH:MM (24h)."}
        else:
            return {"reply": "Fecha inválida. Usa formato YYYY-MM-DD."}

    if state == "awaiting_time":
        if _looks_like_time(message):
            pending["time"] = message.strip()
            database.set_user_state(user_id, "confirm", pending)
            s = pending.get("specialty")
            d = pending.get("date")
            t = pending.get("time")
            return {"reply": f"Confirma: cita de {s} el {d} a las {t}. Responde 'sí' para confirmar o 'cancelar' para cancelar."}
        else:
            return {"reply": "Hora inválida. Usa formato HH:MM (24h)."}

    if state == "confirm":
        if text in ("si", "sí", "s", "ok", "confirmar") or text.startswith("si"):
            appt = {
                "user_id": user_id,
                "patient_name": user.get("name", ""),
                "specialty": pending.get("specialty"),
                "date": pending.get("date"),
                "time": pending.get("time"),
                "status": "scheduled",
            }
            appt_id = database.save_appointment(appt)
            database.set_user_state(user_id, "idle", {})
            return {"reply": f"Cita confirmada. ID: {appt_id}. Te esperamos."}
        else:
            return {"reply": "No se confirmó la cita. Escribe 'sí' para confirmar o 'cancelar' para cancelar."}

    # Fallback
    return {"reply": "No entendí. Puedo ayudarte a reservar una cita: escribe 'quiero una cita'."}
