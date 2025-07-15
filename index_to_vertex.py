# index_to_vertex.py (v3.0 - Arquitectura Final y Verificada)
import os
import re
import json
import time
from sentence_transformers import SentenceTransformer
import pypdf
from google.cloud import aiplatform, storage
from google.api_core import exceptions

import config


def index_documents_to_vertex():
    """
    Implementa el flujo completo de Actualización por Lotes para Vertex AI:
    1. Procesa PDFs locales.
    2. Calcula embeddings.
    3. Crea un archivo JSONL.
    4. Sube el archivo JSONL a Google Cloud Storage.
    5. Invoca la actualización del índice de Vertex AI para que lea desde GCS.
    """
    print("🚀 Iniciando proceso de indexación a Vertex AI (Modo Lote Robusto)...")

    # --- 1. Cargar y procesar los documentos ---
    all_chunks = []
    docs_dir = config.DOCS_DIR
    if not os.path.exists(docs_dir):
        print(f"❌ ERROR: La carpeta de documentos '{docs_dir}' no existe. Ejecuta 'build_knowledge_base.py' primero.")
        return

    for filename in sorted(os.listdir(docs_dir)):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(docs_dir, filename)
            print(f"  -> Procesando: {filename}")
            try:
                with open(pdf_path, 'rb') as file:
                    reader = pypdf.PdfReader(file, strict=False)
                    text = "".join(page.extract_text() or "" for page in reader.pages)
                chunks = [chunk.strip() for chunk in re.split(r'\n\s*\n', text) if
                          len(chunk.split()) > config.PDF_CHUNK_SIZE_THRESHOLD]
                all_chunks.extend([{"text": chunk, "source": filename} for chunk in chunks])
            except Exception as e:
                print(f"     [WARN] No se pudo leer el PDF {filename}: {e}")

    if not all_chunks:
        print("❌ No se encontraron fragmentos de texto para indexar.")
        return
    print(f"✅ {len(all_chunks)} fragmentos de texto extraídos.")

    # --- 2. Calcular los embeddings ---
    print("🧠 Calculando embeddings...")
    embedding_model = SentenceTransformer(config.EMBEDDING_MODEL_NAME, device=config.DEVICE)
    texts_to_embed = [chunk['text'] for chunk in all_chunks]
    embeddings = embedding_model.encode(texts_to_embed, show_progress_bar=True)
    print("✅ Embeddings calculados.")

    # --- 3. Preparar el archivo JSONL localmente ---
    # El nombre del archivo local no es tan importante, pero lo mantenemos por claridad.
    local_jsonl_filename = f"data_{int(time.time())}.json"
    with open(local_jsonl_filename, "w", encoding="utf-8") as f:
        for i, chunk in enumerate(all_chunks):
            datapoint = {
                "id": f"doc_{int(time.time())}_{i}",
                "embedding": embeddings[i].tolist(),
                "restricts": [
                    {"namespace": "text", "allow_list": [chunk['text']]},
                    {"namespace": "source", "allow_list": [chunk['source']]}
                ]
            }
            f.write(json.dumps(datapoint) + "\n")
    print(f"📄 Archivo de datos local '{local_jsonl_filename}' creado.")

    # --- 4. Subir el archivo JSONL a Google Cloud Storage ---
    bucket_name = config.GCS_STAGING_BUCKET_NAME
    # La carpeta dentro del bucket donde subiremos los datos
    gcs_folder = "vertex_ai_staging"
    destination_blob_name = f"{gcs_folder}/{local_jsonl_filename}"

    print(f"☁️ Subiendo archivo de datos a GCS: gs://{bucket_name}/{destination_blob_name}")
    try:
        storage_client = storage.Client(project=config.GOOGLE_PROJECT_ID)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(local_jsonl_filename)
        print("✅ Archivo subido a GCS.")
    except Exception as e:
        print(f"❌ ERROR al subir a GCS: {e}")
        os.remove(local_jsonl_filename)  # Limpiar
        return
    finally:
        os.remove(local_jsonl_filename)  # Limpiar siempre el archivo local

    # --- 5. Invocar la Actualización por Lotes en Vertex AI ---
    gcs_uri_for_vertex = f"gs://{bucket_name}/{gcs_folder}"
    print(f"🔗 Invocando actualización por lotes en Vertex AI desde el directorio: {gcs_uri_for_vertex}")
    try:
        aiplatform.init(project=config.GOOGLE_PROJECT_ID, location=config.GOOGLE_REGION)

        index = aiplatform.MatchingEngineIndex(index_name=config.VERTEX_INDEX_ID)

        # Esta es la llamada correcta para una actualización por lotes.
        # Le pasamos el URI del DIRECTORIO en GCS.
        index.update_embeddings(
            contents_delta_uri=gcs_uri_for_vertex
        )

        print("🎉 ¡Proceso de indexación iniciado en Vertex AI! Puede tardar varios minutos en completarse en la nube.")
        print("   Puedes monitorear el progreso en la consola de Google Cloud en la sección de tu índice.")
    except exceptions.GoogleAPICallError as e:
        print(f"❌ ERROR al invocar la indexación en Vertex AI: {e}")
        print(
            "   Verifica que los IDs de Proyecto, Región e Índice en 'config.py' son correctos y que el bucket existe.")
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado: {e}")


if __name__ == "__main__":
    index_documents_to_vertex()