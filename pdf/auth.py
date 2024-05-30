# auth.py
from flask import request, jsonify
from google.oauth2 import id_token
from google.auth.transport import requests
from functools import wraps

CLIENT_ID = "GOOGLE_CLIENT_ID_PLACEHOLDER"

def authenticate_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "No token provided"}), 401
        try:
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)
            request.user = idinfo
        except ValueError as e:
            return jsonify({"error": str(e)}), 403
        return f(*args, **kwargs)
    return decorated_function
