# Dockerfile

# Usamos la imagen slim, que es pequeña y segura.
FROM python:3.12-slim

WORKDIR /app

# Copia solo los requerimientos primero para el caché de Docker
COPY requirements.txt .

# Instala las dependencias. Gracias al cambio en requirements.txt,
# esto será mucho más rápido y no compilará PyMuPDF.
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código
COPY . .

# Pre-calienta el caché del modelo para arranques rápidos en Cloud Run
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2', cache_folder='./model_cache')"

EXPOSE 8080
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]