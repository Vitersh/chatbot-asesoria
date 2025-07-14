# A.I. Asesor Tributario Chile

Este es un chatbot experto en la legislación tributaria y contable de Chile, construido con una arquitectura RAG y potenciado por la API de Google Gemini.

## Características

- **Cerebro de IA:** Google Gemini
- **Base de Conocimiento:** Híbrida (Biblioteca Maestra de PDFs + Búsqueda en Google)
- **Glosario Interno:** Para máxima precisión terminológica.
- **Interfaz:** API RESTful lista para ser desplegada en la nube.

## Instalación y Ejecución

1.  **Clonar el Repositorio:**
    ```bash
    git clone https://github.com/Vitersh/chatbot-asesoria.git
    cd chatbot-asesoria
    ```

2.  **Crear un Entorno Virtual:**
    ```bash
    python -m venv chatbot_env
    source chatbot_env/bin/activate  # En Windows: chatbot_env\Scripts\activate
    ```

3.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
    *Nota: Si tienes una GPU NVIDIA, asegúrate de instalar la versión de PyTorch con soporte para CUDA por separado.*

4.  **Configurar las Claves de API:**
    - Renombra el archivo `config.py.example` a `config.py`.
    - Abre `config.py` y pega tus claves de API de Google Search y Google Gemini en los campos correspondientes.

5.  **Construir la Base de Conocimiento Local:**
    - Ejecuta el script para crear los PDFs necesarios.
    ```bash
    python build_knowledge_base.py # O el nombre que le hayas dado
    ```

6.  **Ejecutar la API Localmente:**
    ```bash
    uvicorn api:app --reload
    ```
    La API estará disponible en `http://127.0.0.1:8000`.