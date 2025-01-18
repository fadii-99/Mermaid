from django.db import models
from django.core.validators import MinLengthValidator, RegexValidator, EmailValidator
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import timedelta

class User(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # Consider hashing passwords
    occupation = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    organisation = models.CharField(max_length=150, blank=True, null=True)
    registration_number = models.CharField(max_length=50, blank=True, null=True)
    intro = models.BooleanField( blank=True, null=True)

    
    def set_password(self, password):
        self.password = make_password(password)
        self.save()

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.first_name + " " + self.last_name

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'


class ContactUs(models.Model):
    name = models.CharField(
        max_length=100,
        help_text="Enter your full name"
    )
    
    email = models.EmailField(
        max_length=255,
        help_text="Enter a valid email address"
    )
    
    message = models.TextField(
        help_text="Enter your message"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="The time this message was created"
    )

    def __str__(self):
        return f"Message from {self.name} ({self.email})"

    class Meta:
        verbose_name = 'Contact Us'
        verbose_name_plural = 'Contact Us Messages'
        ordering = ['-created_at']




