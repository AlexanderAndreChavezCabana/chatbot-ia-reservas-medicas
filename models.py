from pydantic import BaseModel
from typing import Optional, List


class CreateUserRequest(BaseModel):
    user_id: str
    name: str


class UserResponse(BaseModel):
    user_id: str
    name: str
    created_at: str
    state: Optional[str] = None


class ChatRequest(BaseModel):
    user_id: str
    message: str


class AppointmentCreateRequest(BaseModel):
    specialty: str
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    patient_name: Optional[str] = None


class Appointment(BaseModel):
    appointment_id: str
    user_id: str
    patient_name: str
    specialty: str
    date: str
    time: str
    status: str


class AppointmentResponse(BaseModel):
    appointment_id: str
    message: str
