# Dockerfile (v3.0 - Serverless con ChromaDB en Memoria)
FROM python:3.12-slim

WORKDIR /app

# Copiar solo los requerimientos primero para aprovechar el caché de Docker
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el resto del proyecto
# Esto incluye la carpeta 'documentos/' con nuestros PDFs
COPY . .

# Expone el puerto y ejecuta la API
EXPOSE 8080
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]