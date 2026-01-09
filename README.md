Chatbot de Reservas Médicas (Proyecto)

Proyecto ejemplo que implementa un chatbot de reservas médicas con FastAPI y almacenamiento JSON local.

Características:
- Crear usuario
- Flujo conversacional básico para agendar citas (especialidad, fecha, hora, confirmación)
- Persistencia de citas en `data/appointments.json`
- Endpoints: `POST /users`, `POST /chat`, `GET /appointments/{user_id}`

Instrucciones rápidas:

1. Crear entorno virtual e instalar dependencias:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2. Levantar servidor:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

3. Usar `POST /users` para crear un usuario y luego `POST /chat` para iniciar una reserva.

Advertencia: Este proyecto es un ejemplo educativo. No almacenes información sensible (como datos médicos sensibles) en entornos públicos sin cifrado apropiado.
