from .models import User, ContactUs
from rest_framework.response import Response #type: ignore
from rest_framework.decorators import api_view, permission_classes  #type: ignore
from datetime import datetime, timedelta
from rest_framework import status
from accounts.auth_jwt import decode_jwt_token, generate_jwt_token
from django.http import JsonResponse
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError





def authData(user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    return {
        'message': 'Success',
        'userId': user.id,
        'userName': user.username,
        'email': user.email,
        }



@api_view(['POST'])
def Authentication(request):
    token = request.headers.get('Authorization')
    try:
        decodedToken = decode_jwt_token(token.replace('Bearer ', ''))
        user_id = decodedToken['user_id']
    except:
        return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)

    data = authData(user_id)

    return JsonResponse(data, status=status.HTTP_200_OK)


@api_view(['POST'])
def register_user(request):
    print("Received data:", request.data)
    password = request.data.get('password')
    password2 = request.data.get('password')
    email = request.data.get('email')
    first_name = request.data.get('firstName')
    last_name = request.data.get('lastName')
    occupation = request.data.get('occupation')
    country = request.data.get('country')
    organisation = request.data.get('organisation')
    registration_number = request.data.get('registrationNumber')

    required_fields = [ password, password2, email, first_name, last_name, occupation, country, organisation, registration_number]
    if not all(required_fields):
        return JsonResponse({"error": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

    if password != password2:
        return JsonResponse({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)


    if User.objects.filter(email=email).exists():
        return JsonResponse({"error": "Email already exists."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        validate_password(password)
    except ValidationError:
        return JsonResponse({"error": "Password you entered is too weak."}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create(
        email=email,
        first_name=first_name,
        last_name=last_name,
        occupation=occupation,
        country=country,
        organisation=organisation,
        registration_number=registration_number,
        intro=1
    )
    user.set_password(password)
    user.save()

    return JsonResponse({"message": "User registered successfully."}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def login_user(request):
    print(request.data)
    email = request.data.get('username')

    password = request.data.get('password')

    if not email or not password:
        return JsonResponse({"error": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(email=email).first()

    if user is not None and user.check_password(password):
        token = generate_jwt_token(user)
        user.intro =0
        user.save()
        return JsonResponse({"token": str(token), 'username':user.first_name + " " + user.last_name, 'email':user.email, 'intro':user.intro}, status=status.HTTP_200_OK)
    else:
        return JsonResponse({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
    




























