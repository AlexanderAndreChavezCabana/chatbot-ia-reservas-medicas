from fastapi import FastAPI, HTTPException
from reservas_models import CreateUserRequest, UserResponse, ChatRequest
import reservas_database as database
from reservas_llm import ChatbotService

app = FastAPI(title="Reservas Médicas - Chatbot", version="0.1")


@app.on_event("startup")
def startup_event():
    database.ensure_data()


@app.post("/users", response_model=UserResponse)
def create_user(req: CreateUserRequest):
    try:
        user = database.create_user(req.user_id, req.name)
        return UserResponse(**user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/chat")
def chat(req: ChatRequest):
    if not database.user_exists(req.user_id):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    # Use LLM adapter which includes FAQ and flow
    chatbot = ChatbotService()
    resp = chatbot.handle_chat(req.user_id, req.message)
    return resp


@app.get("/appointments/{user_id}")
def get_appointments(user_id: str):
    if not database.user_exists(user_id):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    appts = database.get_user_appointments(user_id)
    return {"user_id": user_id, "appointments": appts}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
