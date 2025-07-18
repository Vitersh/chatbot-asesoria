# api.py

# --- 1. Importaciones ---
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware # <--- 1. IMPORTAR
from pydantic import BaseModel
import main_chatbot_logic
import rate_limiter

# --- 2. Definición de los Modelos de Datos ---
class QueryRequest(BaseModel):
    question: str
    history: list[dict] = []

class QueryResponse(BaseModel):
    answer: str

# --- 3. Creación de la Aplicación FastAPI---
app = FastAPI(
    title="A.I. Asesor API",
    description="Una API para interactuar con el Asesor Tributario experto en legislación chilena.",
    version="1.1.0"
)

# --- 3.5. Configuración de CORS ---

origins = [
    "https://chatbot-frontend-app-206802478485.southamerica-west1.run.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 4. Evento de Inicio (Startup) ---
@app.on_event("startup")
def startup_event():
    """Carga los modelos, la base de datos Y EL SISTEMA DE LÍMITES."""
    main_chatbot_logic.initialize_system()
    rate_limiter.initialize_firebase()

# --- 5. El "Endpoint" o Punto de Acceso---
@app.post("/ask", response_model=QueryResponse)
def ask_question(query: QueryRequest, user_id: str = Depends(rate_limiter.rate_limit_dependency)):
    """
    Recibe una pregunta, la procesa y devuelve la respuesta.
    La dependencia 'rate_limit_dependency' se ejecuta PRIMERO.
    """
    print(f"[API] Petición permitida para el usuario: '{user_id}'. Procesando pregunta: '{query.question}'")
    try:
        response_text = main_chatbot_logic.get_response(query.question, query.history)
        return {"answer": response_text}
    except Exception as e:
        print(f"[API ERROR] Ocurrió un error al procesar la pregunta: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")

# --- 6. Endpoint de Verificación ---
@app.get("/")
def read_root():
    return {"status": "A.I. Asesor API (v1.1 con Rate Limiting) está funcionando correctamente."}
