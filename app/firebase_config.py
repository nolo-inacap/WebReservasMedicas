# firebase_config.py
import firebase_admin
from firebase_admin import credentials, firestore
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


cred_path = os.path.join(BASE_DIR, 'config', 'firebaseKey')
cred = credentials.Certificate(cred_path)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

# Inicializa el cliente de Firestore
db = firestore.client()