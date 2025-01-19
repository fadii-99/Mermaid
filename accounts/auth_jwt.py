import jwt
from datetime import datetime, timedelta
from django.conf import settings
from jwt import ExpiredSignatureError


def generate_jwt_token(user):
    expiration_time = datetime.now() + timedelta(hours=10)

    payload = {
        'user_id': user.id,
        'exp': int(expiration_time.timestamp()) 
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    return token


def decode_jwt_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except ExpiredSignatureError:
        return {'error': 'Token expired'}


def validate_token(request):
    token = request.headers.get('Authorization')
    if token:
        token = token.replace('Bearer ', '')
        decoded_token = decode_jwt_token(token)
        if 'error' not in decoded_token:
            return True, decoded_token
        else:
            return False, decoded_token
    return False, {'error': 'No token provided'}

def refresh_jwt_token(token):
    payload = decode_jwt_token(token)

    refreshed_token = generate_jwt_token(payload['user_id'])

    return refreshed_token
