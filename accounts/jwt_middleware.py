# import jwt
# from django.conf import settings
# from django.http import JsonResponse
# from datetime import datetime
# from rest_framework import status

# class JWTAuthenticationMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         # Process the request
#         response = self.process_request(request)
#         if response:
#             return response
#         return self.get_response(request)

#     def process_request(self, request):
#         # Exclude paths that do not require token authentication
#         if request.path_info in ['/api/login', '/api/register']:
#             return None

#         token = request.headers.get('Authorization')
#         if not token or not token.startswith('Bearer '):
#             return JsonResponse({'error': 'Authorization token is missing or invalid'}, status=status.HTTP_401_UNAUTHORIZED)

#         try:
#             token = token.replace('Bearer ', '')
#             decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
#             if datetime.now().timestamp() > decoded_token['exp']:
#                 return JsonResponse({'error': 'Token expired'}, status=status.HTTP_401_UNAUTHORIZED)
#             request.user_id = decoded_token['user_id']
#         except jwt.ExpiredSignatureError:
#             return JsonResponse({'error': 'Token expired'}, status=status.HTTP_401_UNAUTHORIZED)
#         except jwt.InvalidTokenError:
#             return JsonResponse({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)

#         return None
