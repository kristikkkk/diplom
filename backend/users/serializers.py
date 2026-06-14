"""Сериализаторы регистрации, входа и отображения пользователя для REST API."""
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Валидация пароля при регистрации и создание пользователя через менеджер модели."""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm', 'role', 'phone_number')

    def validate(self, attrs):
        """Проверяет совпадение пароля и подтверждения."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Пароли не совпадают")
        return attrs

    def create(self, validated_data):
        """Создаёт пользователя с хешированным паролем без поля подтверждения."""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    """Ответ API с полями профиля без чувствительных данных."""
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'avatar', 'phone_number', 
                 'is_verified', 'date_joined', 'last_login')
        read_only_fields = ('id', 'date_joined', 'last_login')


class UserLoginSerializer(serializers.Serializer):
    """Вход по email/паролю с проверкой активности и помещением User в validated_data."""
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        """Аутентифицирует пользователя по email (USERNAME_FIELD) и паролю."""
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Неверные учетные данные')
            if not user.is_active:
                raise serializers.ValidationError('Аккаунт деактивирован')
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Необходимо указать email и пароль')


