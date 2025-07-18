# rate_limiter.py
import datetime
import json
import firebase_admin
from firebase_admin import credentials, firestore, auth
from fastapi import Request, HTTPException, Header, Depends

# Importamos el cliente de Secret Manager y la configuración
from google.cloud import secretmanager
import config

# --- Constantes de Límites ---
LIMIT_AUTHENTICATED = 15
LIMIT_ANONYMOUS = 5

# Conexión a la base de datos de Firestore
db = None


def initialize_firebase():
    """
    Inicializa la app de Firebase Admin cargando las credenciales
    de forma segura desde Google Cloud Secret Manager.
    """
    global db
    try:
        # 1. Crear el cliente para Secret Manager
        client = secretmanager.SecretManagerServiceClient()

        # 2. Construir la ruta completa al secreto
        secret_version_name = f"projects/{config.GOOGLE_PROJECT_ID}/secrets/{config.FIREBASE_SECRET_NAME}/versions/latest"

        # 3. Acceder al secreto
        response = client.access_secret_version(name=secret_version_name)

        # 4. Decodificar el contenido del secreto y cargarlo como un diccionario JSON
        credentials_json = response.payload.data.decode("UTF-8")
        credentials_dict = json.loads(credentials_json)

        # 5. Inicializar Firebase con el diccionario de credenciales
        cred = credentials.Certificate(credentials_dict)

        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("[INFO] Conexión con Firebase y Firestore establecida (Credenciales desde Secret Manager).")

    except Exception as e:
        print(f"[ERROR] No se pudo inicializar Firebase desde Secret Manager: {e}")
        db = None


@firestore.transactional
def check_and_update_limit_in_transaction(transaction, doc_ref, limit):
    """
    Función transaccional para leer y actualizar el contador de forma atómica.
    """
    snapshot = doc_ref.get(transaction=transaction)

    if snapshot.exists:
        current_count = snapshot.get('count')
        if current_count >= limit:
            return False  # Límite excedido

        transaction.update(doc_ref, {'count': firestore.Increment(1)})
    else:
        transaction.set(doc_ref, {'count': 1, 'limit': limit})

    return True  # Petición permitida


async def rate_limit_dependency(
    request: Request,
    Authorization: str = Header(None),
    x_visitor_id: str = Header(None, alias="X-Visitor-ID") # <--- 1. Recibe la cabecera
):
    """
    Dependencia de FastAPI para verificar el límite de peticiones.
    """
    if not db:
        print("[WARN] Firestore no está disponible. Saltando verificación de límite.")
        # Para evitar que la falta de DB detenga la app, podrías retornar un ID temporal
        return "temp_user_db_unavailable"

    user_id = None
    limit = LIMIT_ANONYMOUS

    if Authorization and Authorization.startswith("Bearer "):
        token = Authorization.split("Bearer ")[1]
        try:
            decoded_token = auth.verify_id_token(token)
            user_id = decoded_token['uid']
            limit = LIMIT_AUTHENTICATED
            print(f"[AUTH] Usuario autenticado: {decoded_token.get('email', user_id)}")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Token de autenticación inválido o expirado: {e}")

    if not user_id:
        # 2. Usa el visitorId si existe, si no, usa la IP como último recurso.
        if x_visitor_id:
            user_id = x_visitor_id
            limit = LIMIT_ANONYMOUS
            print(f"[AUTH] Usuario anónimo por Visitor-ID: {user_id}")
        else:
            # Fallback por si la cabecera no llega
            user_id = request.client.host
            limit = LIMIT_ANONYMOUS
            print(f"[AUTH] Usuario anónimo por IP (fallback): {user_id}")

    today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    doc_id: str = f"{user_id}_{today}"
    doc_ref = db.collection('daily_requests').document(doc_id)

    transaction = db.transaction()
    is_request_allowed = check_and_update_limit_in_transaction(transaction, doc_ref, limit)

    if not is_request_allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Límite de {limit} peticiones diarias alcanzado. Vuelve a intentarlo mañana."
        )

    return user_id