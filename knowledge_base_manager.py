# knowledge_base_manager.py
import os
import re
import pypdf
import chromadb
from google.cloud import storage
from googleapiclient.discovery import build
from sentence_transformers import SentenceTransformer

import config


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrae texto de un archivo PDF usando la librería pypdf, más segura."""
    try:
        with open(pdf_path, 'rb') as file:
            reader = pypdf.PdfReader(file, strict=False)
            if reader.is_encrypted:
                try:
                    reader.decrypt('')
                except Exception:
                    print(f"[WARN] No se pudo desencriptar el PDF: {os.path.basename(pdf_path)}")
                    return ""
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
    except Exception as e:
        print(f"[ERROR] No se pudo leer el PDF {os.path.basename(pdf_path)}: {e}")
        return ""


def search_web(query: str) -> str:
    """Realiza una búsqueda web usando la API de Google Custom Search para alta fiabilidad."""
    print(f"[INFO] Realizando búsqueda con Google API para: '{query}'")
    try:
        if not config.GOOGLE_API_KEY or "Pega_aqui" in config.GOOGLE_API_KEY:
            error_msg = "Error: La API Key de Google Search no está configurada en config.py."
            print(f"[ERROR] {error_msg}")
            return error_msg
        if not config.GOOGLE_CSE_ID or "Pega_aqui" in config.GOOGLE_CSE_ID:
            error_msg = "Error: El CSE ID de Google Search no está configurado en config.py."
            print(f"[ERROR] {error_msg}")
            return error_msg

        service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
        res = service.cse().list(q=query, cx=config.GOOGLE_CSE_ID, num=3).execute()
        items = res.get('items', [])

        if not items:
            warning_msg = f"ADVERTENCIA: La búsqueda en Google no arrojó resultados para '{query}'."
            print(f"[WARN] {warning_msg}")
            return warning_msg

        context_str = "CONTEXTO OBTENIDO DE BÚSQUEDA WEB (GOOGLE):\n"
        for i, item in enumerate(items):
            title = item.get('title', 'N/A')
            snippet = item.get('snippet', '').replace('\n', ' ').strip()
            link = item.get('link', 'N/A')
            context_str += f"--- Resultado Web {i + 1} ---\n"
            context_str += f"Fuente URL: {link}\n"
            context_str += f"Título: {title}\n"
            context_str += f"Contenido: {snippet}\n\n"

        return context_str

    except Exception as e:
        error_msg = f"Ocurrió un error técnico al llamar a la Google API: {e}"
        print(f"[ERROR] {error_msg}")
        return error_msg


def download_gcs_folder(bucket_name, source_folder, destination_folder):
    """Descarga una carpeta completa desde Google Cloud Storage."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=source_folder))  # Convertir a lista para tener un conteo

        if not blobs:
            print(
                f"[WARN] No se encontraron archivos en GCS en 'gs://{bucket_name}/{source_folder}/'. La base de datos se creará desde cero.")
            return False

        print(f"☁️ Descargando {len(blobs)} archivos de la base de datos desde GCS bucket '{bucket_name}'...")
        for blob in blobs:
            if blob.name.endswith('/'): continue  # Ignorar "carpetas" vacías

            destination_path = os.path.join(destination_folder, os.path.relpath(blob.name, source_folder))
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)

            blob.download_to_filename(destination_path)
        print("✅ Descarga completada.")
        return True
    except Exception as e:
        print(f"❌ ERROR al descargar desde GCS: {e}")
        return False


def get_or_create_chroma_collection(embedding_model: SentenceTransformer):
    """
    Obtiene la colección de ChromaDB. Si se ejecuta en la nube (Cloud Run),
    primero intenta descargar la base de datos desde Google Cloud Storage.
    """
    # La variable de entorno 'K_SERVICE' es establecida automáticamente por Google Cloud Run.
    if os.environ.get("K_SERVICE"):
        print("🚀 Ejecutando en entorno de Cloud Run.")
        bucket_name = "asesor-ia-conocimiento"
        source_folder = "chroma_db"
        destination_folder = config.CHROMA_PATH

        if not os.path.exists(destination_folder):
            download_gcs_folder(bucket_name, source_folder, destination_folder)
    else:
        print("💻 Ejecutando en entorno local.")

    # Carga o crea la colección desde la carpeta local
    client = chromadb.PersistentClient(path=config.CHROMA_PATH)
    collection = client.get_or_create_collection(name=config.CHROMA_COLLECTION_NAME)

    # Si la colección sigue vacía (porque no se descargó o estaba vacía), la crea desde los PDFs.
    if collection.count() == 0:
        print(f"[WARN] La base de datos está vacía. Procesando documentos en '{config.DOCS_DIR}' para poblarla...")

        all_chunks, all_metadatas, all_ids = [], [], []
        chunk_id = 0
        for filename in sorted(os.listdir(config.DOCS_DIR)):
            if filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(config.DOCS_DIR, filename)
                print(f"  -> Procesando: {filename}")
                text = extract_text_from_pdf(pdf_path)
                if not text: continue

                chunks = [chunk.strip() for chunk in re.split(r'\n\s*\n', text) if
                          len(chunk.split()) > config.PDF_CHUNK_SIZE_THRESHOLD]
                for chunk in chunks:
                    all_chunks.append(chunk)
                    all_metadatas.append({"source": filename})
                    all_ids.append(f"chunk_{chunk_id}")
                    chunk_id += 1

        if not all_chunks:
            print("[ERROR] No se pudo extraer contenido útil de los PDFs. La base de conocimiento no se puede crear.")
            return collection

        print(f"[INFO] Creando embeddings para {len(all_chunks)} fragmentos...")
        embeddings = embedding_model.encode(all_chunks, show_progress_bar=True, batch_size=32)

        collection.add(embeddings=embeddings.tolist(), documents=all_chunks, metadatas=all_metadatas, ids=all_ids)

    print(f"[INFO] Colección '{config.CHROMA_COLLECTION_NAME}' cargada con {collection.count()} documentos.")
    return collection


def query_knowledge_base(collection: chromadb.Collection, query: str) -> str:
    """Consulta la base de conocimiento local (ChromaDB) para obtener contexto relevante."""
    if collection.count() == 0: return "La base de conocimiento local (PDFs) está vacía."
    try:
        results = collection.query(query_texts=[query], n_results=3)
        if not results or not results['documents'][
            0]: return "No se encontró información relevante en los documentos locales."

        context_str = "CONTEXTO OBTENIDO DE DOCUMENTOS LOCALES:\n"
        for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
            context_str += f"---\nFuente del Documento: {meta['source']}\n\n{doc}\n"
        return context_str
    except Exception as e:
        print(f"[ERROR] Ocurrió un error al consultar ChromaDB: {e}")
        return "Error al consultar la base de conocimiento local."