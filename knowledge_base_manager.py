# knowledge_base_manager.py
import os
import re
import pypdf
import chromadb
from googleapiclient.discovery import build
from sentence_transformers import SentenceTransformer

import config


def search_web(query: str) -> str:
    """Realiza una búsqueda web usando la API de Google Custom Search."""
    # (Esta función no cambia, puedes mantener la que ya tienes)
    print(f"[INFO] Realizando búsqueda con Google API para: '{query}'")
    try:
        service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
        res = service.cse().list(q=query, cx=config.GOOGLE_CSE_ID, num=3).execute()
        items = res.get('items', [])
        if not items:
            return f"ADVERTENCIA: La búsqueda en Google no arrojó resultados para '{query}'."
        context_str = "CONTEXTO OBTENIDO DE BÚSQUEDA WEB (GOOGLE):\n"
        for item in items:
            context_str += f"---\nFuente URL: {item.get('link', 'N/A')}\nTítulo: {item.get('title', 'N/A')}\nContenido: {item.get('snippet', '').replace('', ' ').strip()}\n\n"
        return context_str
    except Exception as e:
        return f"Error al contactar la API de Google Search: {e}"


def build_chroma_collection_from_pdfs(embedding_model: SentenceTransformer) -> chromadb.Collection:
    """
    Crea una colección de ChromaDB en memoria a partir de los PDFs en la carpeta DOCS_DIR.
    """
    print("[INFO] Creando nueva colección de ChromaDB en memoria...")
    client = chromadb.Client()  # Cliente en memoria, no persistente
    collection = client.get_or_create_collection(name=config.CHROMA_COLLECTION_NAME)

    all_chunks = []
    docs_dir = config.DOCS_DIR
    if not os.path.exists(docs_dir):
        print(f"❌ ERROR: La carpeta de documentos '{docs_dir}' no existe.")
        return collection

    for filename in sorted(os.listdir(docs_dir)):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(docs_dir, filename)
            print(f"  -> Procesando para ChromaDB: {filename}")
            try:
                with open(pdf_path, 'rb') as file:
                    reader = pypdf.PdfReader(file, strict=False)
                    text = "".join(page.extract_text() or "" for page in reader.pages)
                chunks = [chunk.strip() for chunk in re.split(r'\n\s*\n', text) if len(chunk.split()) > 20]
                all_chunks.extend([{"text": chunk, "source": filename} for chunk in chunks])
            except Exception as e:
                print(f"     [WARN] No se pudo leer el PDF {filename}: {e}")

    if not all_chunks:
        print("[WARN] No se extrajo contenido útil de los PDFs.")
        return collection

    print(f"🧠 Calculando embeddings para {len(all_chunks)} fragmentos...")
    texts_to_embed = [chunk['text'] for chunk in all_chunks]
    embeddings = embedding_model.encode(texts_to_embed, show_progress_bar=True, device=config.DEVICE)

    ids = [f"doc_{i}" for i in range(len(all_chunks))]
    metadatas = [{"source": chunk['source'], "text": chunk['text']} for chunk in all_chunks]

    collection.add(embeddings=embeddings.tolist(), ids=ids, metadatas=metadatas)
    print(f"✅ Colección de ChromaDB creada en memoria con {collection.count()} documentos.")
    return collection


def query_knowledge_base(query: str, embedding_model, collection: chromadb.Collection) -> str:
    """Consulta la base de conocimiento en memoria (ChromaDB)."""
    print(f"[INFO] Consultando ChromaDB en memoria para: '{query}'")
    if collection.count() == 0: return "La base de conocimiento local (ChromaDB) está vacía."
    try:
        query_embedding = embedding_model.encode([query], device=config.DEVICE)
        results = collection.query(query_embeddings=query_embedding.tolist(), n_results=3)

        if not results or not results['documents'][
            0]: return "No se encontró información relevante en los documentos locales."

        context_str = "CONTEXTO OBTENIDO DE DOCUMENTOS LOCALES (CHROMA DB):\n"
        for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
            context_str += f"---\nFuente del Documento: {meta['source']}\n\n{doc}\n"
        return context_str
    except Exception as e:
        print(f"[ERROR] Ocurrió un error al consultar ChromaDB: {e}")
        return "Error al consultar la base de conocimiento local."