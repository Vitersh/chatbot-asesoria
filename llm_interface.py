# llm_interface.py
import re

import google.generativeai as genai
from sentence_transformers import SentenceTransformer

import config

# --- GLOSARIO (sin cambios) ---
CONCEPT_GLOSSARY = {
    "IVA": "Impuesto al Valor Agregado (19% en Chile). Grava la venta de bienes y la prestación de servicios. Se declara mensualmente en el Formulario 29.",
    "IDPC": "Impuesto de Primera Categoría. Es el impuesto que pagan las empresas sobre sus utilidades. La tasa varía según el régimen tributario (ej: 10% para Pro Pyme General).",
    "IGC": "Impuesto Global Complementario. Es un impuesto personal, progresivo, que se aplica a la suma de todos los ingresos de una persona natural durante un año (sueldos, honorarios, retiros de utilidades). Se declara en el Formulario 22.",
    "GASTO RECHAZADO": "Un gasto que el SII no considera necesario para producir la renta de la empresa (ej: gastos personales pagados con fondos de la empresa). Estos gastos no rebajan la base imponible y están sujetos a un impuesto castigo del 40% (Art. 21 LIR).",
    "SpA": "Sociedad por Acciones. Tipo de sociedad muy flexible que permite tener uno o más accionistas. Ideal para crecimiento y entrada de inversionistas.",
    "EIRL": "Empresa Individual de Responsabilidad Limitada. Diseñada para un único dueño. La responsabilidad se limita al capital de la empresa.",
    "PPM": "Pago Provisional Mensual. Es un pago anticipado del Impuesto a la Renta que las empresas y profesionales independientes realizan mensualmente.",
    "SII": "Servicio de Impuestos Internos. La entidad fiscalizadora que administra y cobra los impuestos en Chile.",
    "TGR": "Tesorería General de la República. Entidad que recauda y custodia los fondos públicos.",
    "AFP": "Administradora de Fondos de Pensiones.",
    "FONASA": "Fondo Nacional de Salud.",
    "DFL2": "Decreto con Fuerza de Ley 2. Define las 'viviendas económicas' con beneficios tributarios.",
    "8.000 UF": "Límite máximo de ganancia exenta de impuestos por la venta de bienes raíces durante toda la vida de un contribuyente."
}


def configure_gemini():
    """Configura la API de Gemini con la clave."""
    try:
        if not config.GEMINI_API_KEY or "Pega_aqui" in config.GEMINI_API_KEY:
            print("[ERROR] La API Key de Gemini no está configurada en config.py.")
            return None
        genai.configure(api_key=config.GEMINI_API_KEY)
        print("[INFO] API de Gemini configurada correctamente.")
        return True
    except Exception as e:
        print(f"[ERROR] No se pudo configurar la API de Gemini: {e}")
        return None


def load_embedding_model():
    """Carga solo el modelo de embeddings que corre localmente."""
    print("[INFO] Cargando modelo de embeddings (para RAG)...")
    embedding_model = SentenceTransformer(config.EMBEDDING_MODEL_NAME, device=config.DEVICE,
                                          cache_folder="./model_cache")
    return embedding_model


def call_gemini_api(prompt: str, model_name: str = None) -> tuple[str, str]:
    """Llama a la API de Gemini y devuelve una tupla: (estado, texto_respuesta)."""
    if model_name is None:
        model_name = config.GEMINI_MODEL_NAME
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        if not response.parts:
            finish_reason = response.candidates[0].finish_reason.name
            if finish_reason == "SAFETY":
                print(f"[WARN] Respuesta de {model_name} bloqueada por seguridad.")
                return "SAFETY_BLOCK", ""
            else:
                print(f"[WARN] Respuesta de {model_name} vacía. Razón: {finish_reason}")
                return "ERROR", f"La IA devolvió una respuesta vacía (Razón: {finish_reason})."
        return "SUCCESS", response.text
    except Exception as e:
        print(f"[ERROR] Falló la llamada a la API de Gemini ({model_name}): {e}")
        return "ERROR", f"Error al contactar la API de Gemini: {e}"


def decompose_query_for_search(query: str) -> tuple[str, list[str]]:
    """Usa Gemini para descomponer la pregunta. Devuelve estado y lista de queries."""
    print("[INFO] Descomponiendo pregunta con Gemini...")
    prompt = f"""Tu única tarea es descomponer la PREGUNTA DEL USUARIO en un máximo de 3 consultas de búsqueda simples para Google. Responde solo con la lista de consultas, una por línea. No añadas numeración ni explicaciones.

PREGUNTA DEL USUARIO: que pasa con mi devolucion del IVA si debo dinero del CAE? y puedo destinar esta devolucion si está retenida a fonasa o a la AFP ?
Respuesta:
retención devolución IVA por deuda CAE Chile
Tesorería General de la República retención de impuestos
pago cotizaciones previsionales con devolución de impuestos

PREGUNTA DEL USUARIO: {query}
Respuesta:
"""
    status, response_text = call_gemini_api(prompt)
    if status != "SUCCESS":
        return status, []

    search_queries = [line.strip() for line in response_text.split('\n') if line.strip()]
    print(f"[INFO] Pregunta descompuesta en las siguientes búsquedas: {search_queries}")
    return "SUCCESS", search_queries


def generate_final_response(prompt: str) -> tuple[str, str]:
    """Genera la respuesta final usando Gemini."""
    print("[INFO] Generando respuesta final con Gemini...")
    return call_gemini_api(prompt)


def inject_glossary_definitions(query: str, context: str) -> str:
    """Busca acrónimos del glosario en la pregunta y los inyecta en el contexto."""
    injected_definitions = ""
    for term, definition in CONCEPT_GLOSSARY.items():
        if re.search(r'\b' + re.escape(term) + r'\b', query, re.IGNORECASE):
            injected_definitions += f"- {term}: {definition}\n"
    if injected_definitions:
        print(f"[INFO] Inyectando definiciones del glosario.")
        return f"GLOSARIO DE CONCEPTOS CLAVE (Máxima Prioridad):\n{injected_definitions}\n---\n{context}"
    return context


def sanitize_query_for_safety(query: str) -> tuple[str, str]:
    """Usa Gemini para re-escribir una pregunta bloqueada a una versión neutral."""
    print("[INFO] Pregunta original bloqueada. Intentando re-formulación neutral...")
    prompt = f"""Tu única tarea es re-escribir la siguiente PREGUNTA ORIGINAL, que fue bloqueada por filtros de seguridad. Elimina palabras sensibles como 'evasión', 'sin declarar', 'perdonazo' o 'trucos', y reemplázalas por terminología técnica y neutral como 'obligaciones tributarias', 'tratamiento fiscal', 'beneficios tributarios' o 'planificación fiscal'. Mantén la intención original de la consulta. Responde solo con la pregunta re-formulada.

PREGUNTA ORIGINAL: Arriendo en efectivo y no lo declaro al SII, ¿qué multas me pueden pasar?
RESPUESTA RE-FORMULADA: ¿Cuáles son las obligaciones tributarias y las posibles contingencias al recibir ingresos por arriendo no declarados ante el SII?

PREGUNTA ORIGINAL: {query}
RESPUESTA RE-FORMULADA:
"""
    status, reformulated_query = call_gemini_api(prompt, model_name="gemini-1.5-flash-latest")
    if status == "SUCCESS":
        print(f"[INFO] Pregunta re-formulada: {reformulated_query}")
    return status, reformulated_query


def build_final_prompt(user_query: str, combined_context: str, history: list) -> str:
    """Prompt v12.1: Refinado para respuestas más conclusivas."""
    hist_str = "".join(f"Usuario: \"{turn['user']}\"\nAsesor: \"{turn['assistant']}\"\n" for turn in
                       history[-config.HISTORY_MAX_TURNS:])
    return f"""Eres "A.I. Asesor", un experto en tributación de Chile. Tu razonamiento es transparente y te basas en hechos.

**PROCESO DE RAZONAMIENTO Y RESPUESTA:**
Sigue este formato de manera obligatoria.

### Pensamiento
1.  **Preguntas Clave:** Enumera las dudas concretas del usuario.
2.  **Hechos Extraídos del Contexto:** Cita textualmente o resume los fragmentos del GLOSARIO y del CONTEXTO que responden directamente a las preguntas clave. El GLOSARIO tiene la máxima prioridad.
3.  **Síntesis y Plan de Respuesta:** Basado en los hechos, explica cómo conectarás la información para construir una respuesta coherente. Si los hechos apuntan a una recomendación estratégica clara (ej: elegir SpA sobre EIRL para crecer), decláralo aquí. Si la información es insuficiente, indícalo.

### Respuesta Final
Ahora, sintetiza tu 'Plan de Respuesta' en un texto final, claro, profesional y bien redactado para el usuario. **Sé directo y conclusivo si la evidencia lo permite.** No copies el texto del Pensamiento; redáctalo de nuevo. Empieza directamente con la información. Cita tus fuentes y concluye siempre con la advertencia de consultar a un profesional. Si no tienes información suficiente, responde únicamente: `Basado en la información disponible, no tengo una respuesta para tu consulta.`

---
CONTEXTO:
{combined_context}
---
HISTORIAL DE CONVERSACIÓN RECIENTE:
{hist_str if hist_str else "No hay historial reciente."}
---
PREGUNTA ACTUAL DEL USUARIO:
"{user_query}"
"""