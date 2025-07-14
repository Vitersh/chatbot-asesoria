# api.py

# --- 1. Importaciones ---
# Importamos las herramientas que necesitamos.
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import main_chatbot_logic  # Importamos el "motor" de nuestro chatbot
import config  # Importamos nuestra configuración


# --- 2. Definición de los Modelos de Datos ---
# Esto le dice a FastAPI cómo deben ser los datos que entran y salen.
# Es como definir la forma del "enchufe".

class QueryRequest(BaseModel):
    """Define la estructura de una pregunta que llega a la API."""
    question: str
    # El historial es una lista de diccionarios, pero es opcional.
    history: list[dict] = []


class QueryResponse(BaseModel):
    """Define la estructura de la respuesta que la API enviará de vuelta."""
    answer: str


# --- 3. Creación de la Aplicación FastAPI ---
# Esta es la línea principal que crea nuestro servidor web.
app = FastAPI(
    title="A.I. Asesor API",
    description="Una API para interactuar con el Asesor Tributario experto en legislación chilena.",
    version="1.0.0"
)


# --- 4. Evento de Inicio (Startup) ---
# Esta es una función especial que se ejecuta UNA SOLA VEZ, cuando el servidor arranca.
# Es el lugar perfecto para cargar los modelos y la base de datos, para que no se carguen con cada pregunta.
@app.on_event("startup")
def startup_event():
    """Carga todos los modelos y la base de datos al iniciar la API."""
    # Llamamos a la función de inicialización que crearemos en nuestro archivo de lógica.
    main_chatbot_logic.initialize_system()


# --- 5. El "Endpoint" o Punto de Acceso ---
# Esta es la URL específica donde se pueden hacer las preguntas.
# En este caso, será http://tu-direccion/ask
@app.post("/ask", response_model=QueryResponse)
def ask_question(query: QueryRequest):
    """
    Recibe una pregunta, la procesa con el motor del chatbot y devuelve la respuesta.
    """
    print(f"[API] Recibida pregunta: '{query.question}'")
    try:
        # Llamamos a la función principal de nuestro motor, pasándole la pregunta y el historial.
        response_text = main_chatbot_logic.get_response(query.question, query.history)

        # Devolvemos la respuesta en el formato que definimos en QueryResponse.
        return {"answer": response_text}
    except Exception as e:
        # Si algo sale mal, devolvemos un error claro.
        print(f"[API ERROR] Ocurrió un error al procesar la pregunta: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")


# --- 6. Endpoint de Verificación (Opcional pero recomendado) ---
# Una URL simple para verificar que la API está funcionando.
@app.get("/")
def read_root():
    return {"status": "A.I. Asesor API está funcionando correctamente."}