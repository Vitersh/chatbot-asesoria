# 1. Usar una imagen base oficial de Python
FROM python:3.12-slim

# 2. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiar el archivo de requerimientos e instalar dependencias
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --install -r requirements.txt

# 4. Copiar todo el código del proyecto al contenedor
COPY . .

# 5. Comando para ejecutar la aplicación (usaremos una API con FastAPI)
# El puerto 8080 es el estándar que Cloud Run espera.
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]