from django.contrib import admin
from django.urls import path
from reportGen import views



urlpatterns = [
    path('intro/', views.form_view),
    path('background/', views.background),
    path('views_obtained/', views.viewsObtained),
    path('assessment/', views.assessment),
    path('generate_report/', views.generate_report),
]