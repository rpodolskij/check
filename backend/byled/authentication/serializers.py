from rest_framework import serializers
from users.models import User


class SignInSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)


class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'phone', 'middle_name', 'company_address', 'company_name', 'position', 'password', 'first_name', 'middle_name', 'last_name' ]
        password = serializers.CharField(required=True, min_length=8)


class ForgotUserSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class RestorePasswordSerializer(serializers.Serializer):
    restore_key = serializers.CharField(required=True)
    password = serializers.CharField(required=True, min_length=8)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
