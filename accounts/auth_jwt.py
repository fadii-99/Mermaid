import jwt
from datetime import datetime, timedelta
from django.conf import settings


def generate_jwt_token(user):
    expiration_time = datetime.now() + timedelta(hours=10)

    payload = {
        'user_id': user.id,
        'username': user.first_name + " " + user.last_name,
        'email': user.email,
        'exp': expiration_time.timestamp(),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    return token


def decode_jwt_token(token):

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    return payload


def refresh_jwt_token(token):
    payload = decode_jwt_token(token)

    new_expiration_time = datetime.now() + timedelta(hours=10)
    payload['exp'] = new_expiration_time.timestamp()

    refreshed_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return refreshed_token
