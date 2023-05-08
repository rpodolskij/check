from rest_framework import serializers

from .models import User, ActionKey



class UserManagerSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        depth = 0
        # fields = '__all__'
        exclude = ['is_staff', 'is_superuser', 'password', 'user_permissions']


class UserSerializer(serializers.ModelSerializer):
    manager = UserManagerSerializer()

    class Meta:
        model = User
        depth = 1
        # fields = '__all__'
        exclude = ['is_staff', 'is_superuser', 'password', 'user_permissions']


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'company_address',
            'company_name',
            'email',
            'first_name',
            'last_name',
            'middle_name',
            'phone',
            'position',
            'avatar',
            'price_level',
            'manager',

        ]


class RestoreKeysSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionKey
        fields = '__all__'


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
