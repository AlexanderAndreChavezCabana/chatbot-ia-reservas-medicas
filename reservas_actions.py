from typing import Dict


def notify_patient(appointment: Dict) -> Dict:
    message = f"Notificación enviada para cita {appointment.get('appointment_id')} el {appointment.get('date')} a las {appointment.get('time')}"
    return {"success": True, "message": message}


def execute_action(action_data: Dict) -> Dict:
    if not action_data:
        return {"success": False, "message": "No action provided"}
    cmd = action_data.get("command")
    if cmd == "notify":
        appt = action_data.get("data", {})
        return notify_patient(appt)
    return {"success": False, "message": "Unknown action"}
