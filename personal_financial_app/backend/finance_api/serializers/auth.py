"""Serializers for authentication: registration and login."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    """
    Validates and creates a new user account.
    Passwords are validated with Django's password validators.
    """
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_username(self, value):
        username = value.strip()
        if not username:
            raise serializers.ValidationError('Username cannot be empty.')
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError('This username is already taken.')
        return username

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )