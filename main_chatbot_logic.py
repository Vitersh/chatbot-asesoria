# main_chatbot_logic.py
import re
import traceback

import knowledge_base_manager
import llm_interface

# --- Variables Globales del Sistema ---
# Estas variables mantendrán los componentes cargados en la memoria del servidor.
collection = None
is_initialized = False


def initialize_system():
    """
    Carga todos los componentes necesarios una sola vez al iniciar la API.
    Esta función es llamada por el evento 'startup' de FastAPI.
    """
    global collection, is_initialized
    if is_initialized:
        print("[INFO] El sistema ya ha sido inicializado.")
        return

    print("\n" + "=" * 60)
    print("💡 INICIALIZANDO SISTEMA A.I. ASESOR (MODO API)...")
    print("=" * 60)

    if not llm_interface.configure_gemini():
        raise RuntimeError("No se pudo configurar la API de Gemini. Revisa la API Key en config.py.")

    try:
        embedding_model = llm_interface.load_embedding_model()
        collection = knowledge_base_manager.get_or_create_chroma_collection(embedding_model)
        is_initialized = True
        print("\n✅ ¡Sistema listo para recibir peticiones!")
    except Exception as e:
        print(f"[FATAL] No se pudieron cargar los componentes locales. Error: {e}")
        traceback.print_exc()
        # En un entorno de producción, esto debería alertar a un administrador.
        is_initialized = False


def get_response(user_input: str, history: list) -> str:
    """
    Función principal que procesa una pregunta y devuelve una respuesta.
    Esta es la lógica central que será llamada por la API.
    """
    if not is_initialized or not collection:
        return "Error: El sistema A.I. Asesor no está inicializado correctamente. Por favor, contacte al administrador."

    try:
        # --- FLUJO DE GENERACIÓN DE RESPUESTA ---
        print(f"\n[LOGIC] Procesando pregunta: '{user_input}'")

        # 1. Obtener contexto (primer intento)
        combined_context = get_context_for_query(user_input, collection)

        # 2. Inyectar glosario y construir prompt
        final_context = llm_interface.inject_glossary_definitions(user_input, combined_context)
        prompt = llm_interface.build_final_prompt(user_input, final_context, history)

        # 3. Generar respuesta (primer intento)
        status, full_response_text = llm_interface.generate_final_response(prompt)

        # 4. Protocolo de Auto-Censura si es necesario
        if status == "SAFETY_BLOCK":
            print("[LOGIC] Bloqueo de seguridad detectado. Iniciando protocolo de auto-censura.")
            status_reform, sanitized_query = llm_interface.sanitize_query_for_safety(user_input)

            if status_reform == "SUCCESS" and sanitized_query:
                print(f"[LOGIC] Re-intentando con pregunta neutral: '{sanitized_query}'")
                combined_context = get_context_for_query(sanitized_query, collection)
                final_context = llm_interface.inject_glossary_definitions(sanitized_query, combined_context)
                prompt = llm_interface.build_final_prompt(sanitized_query, final_context, history)
                status, full_response_text = llm_interface.generate_final_response(prompt)

                aviso = f"(Aviso: Tu pregunta original fue ajustada para cumplir con las políticas de seguridad. La respuesta se basa en la consulta reformulada: '{sanitized_query}')\n\n"
                full_response_text = aviso + full_response_text
            else:
                return "Tu pregunta fue bloqueada por los filtros de seguridad y no se pudo re-formular automáticamente. Por favor, intenta de nuevo con otras palabras."

        # 5. Parseo final de la respuesta
        final_answer = parse_final_answer(full_response_text)

        # (La gestión del historial ahora se haría en la capa de la API o en una base de datos de usuarios)

        return final_answer

    except Exception as e:
        print(f"[LOGIC ERROR] Ocurrió un error crítico al generar la respuesta: {e}")
        traceback.print_exc()
        return "Ocurrió un error inesperado al procesar tu pregunta. Por favor, intenta de nuevo."


def get_context_for_query(query: str, collection):
    """Función auxiliar para obtener el contexto de búsqueda."""
    status, search_queries = llm_interface.decompose_query_for_search(query)

    if status != "SUCCESS":
        print(f"[WARN] No se pudo descomponer la pregunta. Usando la pregunta original.")
        search_queries = [query]
    elif not search_queries:
        search_queries = [query]

    all_web_contexts = [knowledge_base_manager.search_web(q) for q in search_queries]
    final_web_context = "\n\n".join(all_web_contexts)
    local_context = knowledge_base_manager.query_knowledge_base(collection, query)

    return f"{final_web_context}\n\n{local_context}"


def parse_final_answer(full_response_text: str) -> str:
    """Extrae limpiamente el texto de la 'Respuesta Final' del output del LLM."""
    split_response = re.split(r'###\s+Respuesta Final', full_response_text, maxsplit=1, flags=re.IGNORECASE)

    if len(split_response) > 1:
        final_answer = split_response[1].strip()
        # Si hay un aviso de auto-censura, lo mantenemos
        if full_response_text.startswith("(Aviso:"):
            aviso_original = split_response[0].split("### Pensamiento")[0].strip()
            return f"{aviso_original}\n\n{final_answer}"
        return final_answer

    # Si el formato no se encuentra, devuelve el texto completo como fallback
    return full_response_text