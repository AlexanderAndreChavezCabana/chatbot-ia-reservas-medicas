"""
Flujo conversacional para reservas de citas médicas.
"""
from typing import Dict
import re
from datetime import datetime, timedelta
import reservas_database as database


# Especialidades disponibles
SPECIALTIES = {
    "general": "Medicina General",
    "pediatria": "Pediatría", 
    "pediatría": "Pediatría",
    "cardiologia": "Cardiología",
    "cardiología": "Cardiología",
    "dermatologia": "Dermatología",
    "dermatología": "Dermatología",
    "ginecologia": "Ginecología",
    "ginecología": "Ginecología",
    "traumatologia": "Traumatología",
    "traumatología": "Traumatología",
    "oftalmologia": "Oftalmología",
    "oftalmología": "Oftalmología",
    "neurologia": "Neurología",
    "neurología": "Neurología",
    "psicologia": "Psicología",
    "psicología": "Psicología",
    "nutricion": "Nutrición",
    "nutrición": "Nutrición",
}

# Horarios disponibles
AVAILABLE_HOURS = [
    "08:00", "08:30", "09:00", "09:30", "10:00", "10:30",
    "11:00", "11:30", "12:00", "14:00", "14:30", "15:00",
    "15:30", "16:00", "16:30", "17:00", "17:30", "18:00"
]

BOOK_KEYWORDS = ["cita", "reserv", "agend", "turno", "hora", "consulta", "atender", "doctor", "médico", "medico"]


def _normalize_specialty(text: str) -> str:
    """Normaliza el nombre de la especialidad."""
    text_lower = text.lower().strip()
    for key, value in SPECIALTIES.items():
        if key in text_lower or value.lower() in text_lower:
            return value
    return text.strip().title()


def _parse_date(text: str) -> str:
    """Intenta parsear diferentes formatos de fecha."""
    text = text.lower().strip()
    today = datetime.now()
    
    # Palabras clave
    if text in ["hoy", "ahora"]:
        return today.strftime("%Y-%m-%d")
    if text in ["mañana", "manana"]:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if text in ["pasado mañana", "pasado manana"]:
        return (today + timedelta(days=2)).strftime("%Y-%m-%d")
    
    # Formato YYYY-MM-DD
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return text
    except:
        pass
    
    # Formato DD/MM/YYYY o DD-MM-YYYY
    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"]:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d")
        except:
            pass
    
    return None


def _parse_time(text: str) -> str:
    """Intenta parsear diferentes formatos de hora."""
    text = text.lower().strip().replace(" ", "")
    
    # Remover "am", "pm", "hrs", "h"
    text = re.sub(r'(am|pm|hrs|h)$', '', text)
    
    # Formato HH:MM
    try:
        datetime.strptime(text, "%H:%M")
        return text
    except:
        pass
    
    # Formato H:MM
    try:
        dt = datetime.strptime(text, "%H:%M")
        return dt.strftime("%H:%M")
    except:
        pass
    
    # Solo hora (ej: "9", "14")
    try:
        hour = int(text)
        if 0 <= hour <= 23:
            return f"{hour:02d}:00"
    except:
        pass
    
    return None


def _is_valid_date(date_str: str) -> bool:
    """Verifica que la fecha sea válida y futura."""
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return date >= today
    except:
        return False


def _format_specialties_list() -> str:
    """Formatea la lista de especialidades disponibles."""
    unique_specs = sorted(set(SPECIALTIES.values()))
    return "\n".join([f"• {spec}" for spec in unique_specs])


def _format_hours_list() -> str:
    """Formatea los horarios disponibles."""
    morning = [h for h in AVAILABLE_HOURS if int(h.split(":")[0]) < 12]
    afternoon = [h for h in AVAILABLE_HOURS if int(h.split(":")[0]) >= 12]
    return f"🌅 Mañana: {', '.join(morning)}\n🌆 Tarde: {', '.join(afternoon)}"


def process_message(user_id: str, message: str) -> Dict:
    """Procesa mensajes del usuario y maneja el flujo de reserva."""
    user = database.get_user(user_id)
    if not user:
        return {"reply": "⚠️ Usuario no encontrado. Por favor, regístrate primero."}

    state = user.get("state", "idle")
    pending = user.get("pending", {}) or {}
    text = message.lower().strip()

    # === CANCELAR EN CUALQUIER MOMENTO ===
    if any(word in text for word in ["cancelar", "cancel", "salir", "terminar", "no quiero"]):
        database.set_user_state(user_id, "idle", {})
        return {"reply": "❌ Proceso cancelado. ¿En qué más puedo ayudarte?\n\nEscribe 'cita' para agendar una nueva consulta."}

    # === VER CITAS ===
    if any(word in text for word in ["mis citas", "ver citas", "consultar citas", "tengo citas"]):
        appointments = database.get_user_appointments(user_id)
        if appointments:
            reply = "📋 **Tus citas programadas:**\n\n"
            for i, apt in enumerate(appointments, 1):
                reply += f"{i}. **{apt.get('specialty', 'N/A')}**\n"
                reply += f"   📅 {apt.get('date', 'N/A')} a las {apt.get('time', 'N/A')}\n"
                reply += f"   Estado: {apt.get('status', 'N/A')}\n\n"
            return {"reply": reply}
        else:
            return {"reply": "📋 No tienes citas programadas.\n\n¿Te gustaría agendar una? Escribe 'quiero una cita'."}

    # === ESTADO: IDLE ===
    if state == "idle":
        if any(k in text for k in BOOK_KEYWORDS):
            database.set_user_state(user_id, "awaiting_specialty", {})
            specialties_list = _format_specialties_list()
            return {
                "reply": f"👨‍⚕️ ¡Perfecto! Vamos a agendar tu cita.\n\n**¿Qué especialidad necesitas?**\n\n{specialties_list}\n\n_Escribe el nombre de la especialidad o 'cancelar' para salir._"
            }
        else:
            return {
                "reply": "🏥 Soy tu asistente de reservas médicas.\n\nPuedo ayudarte a:\n• 📅 **Agendar cita** - escribe 'quiero una cita'\n• 📋 **Ver mis citas** - escribe 'mis citas'\n• ❓ **Preguntas** - horarios, precios, especialidades\n\n¿Qué deseas hacer?"
            }

    # === ESTADO: ESPERANDO ESPECIALIDAD ===
    if state == "awaiting_specialty":
        specialty = _normalize_specialty(message)
        pending["specialty"] = specialty
        database.set_user_state(user_id, "awaiting_date", pending)
        
        today = datetime.now()
        dates_example = f"• Hoy: {today.strftime('%Y-%m-%d')}\n• Mañana: {(today + timedelta(days=1)).strftime('%Y-%m-%d')}"
        
        return {
            "reply": f"✅ Especialidad: **{specialty}**\n\n📅 **¿Qué fecha prefieres?**\n\nPuedes escribir:\n{dates_example}\n• O cualquier fecha en formato YYYY-MM-DD o DD/MM/YYYY\n\n_Escribe 'cancelar' para salir._"
        }

    # === ESTADO: ESPERANDO FECHA ===
    if state == "awaiting_date":
        parsed_date = _parse_date(message)
        
        if not parsed_date:
            return {
                "reply": "⚠️ No pude entender la fecha.\n\nPor favor usa uno de estos formatos:\n• 'hoy' o 'mañana'\n• YYYY-MM-DD (ej: 2026-01-15)\n• DD/MM/YYYY (ej: 15/01/2026)\n\n_Escribe 'cancelar' para salir._"
            }
        
        if not _is_valid_date(parsed_date):
            return {
                "reply": "⚠️ La fecha debe ser hoy o una fecha futura.\n\nPor favor, elige otra fecha.\n\n_Escribe 'cancelar' para salir._"
            }
        
        pending["date"] = parsed_date
        database.set_user_state(user_id, "awaiting_time", pending)
        hours_list = _format_hours_list()
        
        return {
            "reply": f"✅ Fecha: **{parsed_date}**\n\n🕐 **¿A qué hora prefieres?**\n\nHorarios disponibles:\n{hours_list}\n\n_Escribe la hora (ej: 09:00, 14:30) o 'cancelar' para salir._"
        }

    # === ESTADO: ESPERANDO HORA ===
    if state == "awaiting_time":
        parsed_time = _parse_time(message)
        
        if not parsed_time:
            return {
                "reply": "⚠️ No pude entender la hora.\n\nPor favor usa formato HH:MM (ej: 09:00, 14:30)\n\n_Escribe 'cancelar' para salir._"
            }
        
        if parsed_time not in AVAILABLE_HOURS:
            hours_list = _format_hours_list()
            return {
                "reply": f"⚠️ Ese horario no está disponible.\n\nHorarios disponibles:\n{hours_list}\n\n_Escribe 'cancelar' para salir._"
            }
        
        pending["time"] = parsed_time
        database.set_user_state(user_id, "confirm", pending)
        
        specialty = pending.get("specialty", "N/A")
        date = pending.get("date", "N/A")
        
        return {
            "reply": f"📋 **Resumen de tu cita:**\n\n👨‍⚕️ Especialidad: **{specialty}**\n📅 Fecha: **{date}**\n🕐 Hora: **{parsed_time}**\n👤 Paciente: **{user.get('name', 'N/A')}**\n\n✅ Escribe **'sí'** o **'confirmar'** para reservar\n❌ Escribe **'cancelar'** para cancelar"
        }

    # === ESTADO: CONFIRMAR ===
    if state == "confirm":
        if any(word in text for word in ["si", "sí", "s", "ok", "confirmar", "confirmo", "dale", "listo"]):
            appt = {
                "user_id": user_id,
                "patient_name": user.get("name", ""),
                "specialty": pending.get("specialty"),
                "date": pending.get("date"),
                "time": pending.get("time"),
                "status": "confirmada",
            }
            appt_id = database.save_appointment(appt)
            database.set_user_state(user_id, "idle", {})
            
            return {
                "reply": f"🎉 **¡Cita confirmada exitosamente!**\n\n📋 ID de cita: **{appt_id}**\n👨‍⚕️ {pending.get('specialty')}\n📅 {pending.get('date')} a las {pending.get('time')}\n\n📍 Recuerda:\n• Llegar 15 minutos antes\n• Traer tu DNI y carnet de seguro\n• Resultados de exámenes previos (si los tienes)\n\n¡Te esperamos! 🏥"
            }
        
        if any(word in text for word in ["no", "cambiar", "modificar", "editar"]):
            database.set_user_state(user_id, "awaiting_specialty", {})
            return {
                "reply": "🔄 Vamos a empezar de nuevo.\n\n**¿Qué especialidad necesitas?**\n\n_Escribe 'cancelar' para salir._"
            }
        
        return {
            "reply": "🤔 No entendí tu respuesta.\n\n✅ Escribe **'sí'** para confirmar la cita\n❌ Escribe **'cancelar'** para cancelar\n🔄 Escribe **'cambiar'** para modificar"
        }

    # === FALLBACK ===
    database.set_user_state(user_id, "idle", {})
    return {
        "reply": "🤔 No entendí tu mensaje.\n\nPuedo ayudarte a:\n• 📅 **Agendar cita** - escribe 'quiero una cita'\n• 📋 **Ver mis citas** - escribe 'mis citas'\n• ❓ **Preguntas** - sobre horarios, precios, etc.\n\n¿Qué deseas hacer?"
    }
