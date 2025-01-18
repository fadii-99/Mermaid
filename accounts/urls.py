from django.contrib import admin
from django.urls import path
from accounts import views



urlpatterns = [
    path('signup/', views.register_user),
    path('login/', views.login_user),
]