# main_chatbot_logic.py
import re

import knowledge_base_manager
import llm_interface

# Variables globales del sistema
collection = None
embedding_model = None
is_initialized = False


def initialize_system():
    """
    Carga los componentes y construye la base de datos ChromaDB en memoria.
    """
    global collection, embedding_model, is_initialized
    if is_initialized:
        print("[INFO] El sistema ya ha sido inicializado.")
        return

    print("\n" + "=" * 60)
    print("💡 INICIALIZANDO SISTEMA A.I. ASESOR (MODO CHROMA EN MEMORIA)...")
    print("=" * 60)

    if not llm_interface.configure_gemini():
        raise RuntimeError("No se pudo configurar la API de Gemini.")

    # Cargamos el modelo de embeddings que se usará para todo
    embedding_model = llm_interface.load_embedding_model()

    # Construimos la base de datos ChromaDB a partir de los PDFs
    collection = knowledge_base_manager.build_chroma_collection_from_pdfs(embedding_model)

    is_initialized = True
    print("\n✅ ¡Sistema listo para recibir peticiones!")


def get_response(user_input: str, history: list) -> str:
    """Función principal que procesa una pregunta y devuelve una respuesta."""
    if not is_initialized or not collection:
        return "Error: El sistema no está inicializado correctamente."

    # --- Flujo de RAG ---
    status, search_queries = llm_interface.decompose_query_for_search(user_input)
    if status != "SUCCESS": return "Error al descomponer la pregunta."
    if not search_queries: search_queries = [user_input]

    all_web_contexts = [knowledge_base_manager.search_web(q) for q in search_queries]
    final_web_context = "\n\n".join(all_web_contexts)

    # La consulta ahora necesita el modelo de embeddings y la colección
    local_context = knowledge_base_manager.query_knowledge_base(user_input, embedding_model, collection)

    combined_context = f"{final_web_context}\n\n{local_context}"

    final_context = llm_interface.inject_glossary_definitions(user_input, combined_context)
    prompt = llm_interface.build_final_prompt(user_input, final_context, history)
    status, full_response_text = llm_interface.generate_final_response(prompt)

    # ... (el resto de la lógica de parseo y manejo de seguridad no cambia) ...
    final_answer = full_response_text
    split_response = re.split(r'###\s+Respuesta Final', full_response_text, maxsplit=1, flags=re.IGNORECASE)
    if len(split_response) > 1:
        final_answer = split_response[1].strip()

    return final_answer