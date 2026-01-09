from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from reservas_models import CreateUserRequest, UserResponse, ChatRequest
import reservas_database as database
from reservas_llm import ChatbotService
import os
import json


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.ensure_data()
    yield


app = FastAPI(title="Reservas Médicas - Chatbot", version="0.1", lifespan=lifespan)

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def root():
    return FileResponse(os.path.join(static_dir, "index.html"))


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
    chatbot = ChatbotService()
    resp = chatbot.handle_chat(req.user_id, req.message)
    return resp


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """Endpoint con streaming para respuestas en tiempo real."""
    if not database.user_exists(req.user_id):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    chatbot = ChatbotService()
    
    def generate():
        for chunk in chatbot.handle_chat_stream(req.user_id, req.message):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/appointments/{user_id}")
def get_appointments(user_id: str):
    if not database.user_exists(user_id):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    appts = database.get_user_appointments(user_id)
    return {"user_id": user_id, "appointments": appts}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
