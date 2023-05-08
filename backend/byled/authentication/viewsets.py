from datetime import datetime, timedelta

from django.contrib.auth import authenticate, login, logout
from django.utils import timezone

from rest_framework import viewsets
from rest_framework.request import Request
from django.http.response import HttpResponseRedirect
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework import status

from byled.responses import ApiErrorCodes, ApiResponse, ApiErrorResponse

from users.models import User, ActionKey, ActionEnum

from .serializers import SignInSerializer, ForgotUserSerializer, RestorePasswordSerializer, \
    ChangePasswordSerializer, CreateUserSerializer
from .permissions import CsrfExemptSessionAuthentication

from django.conf import settings
from django.core.mail import send_mail

from utils.logging.logger import info, warning
from drf_yasg.utils import swagger_auto_schema
from drf_yasg.openapi import Parameter



class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    @action(detail=False, methods=['post'])
    @swagger_auto_schema(
        operation_summary='Авторизация зарегистрированного пользователя',
        request_body=SignInSerializer,
        responses={201: None},
        tags=[
            'Аутентификация'
        ]
    )
    def signin(self, request: Request):
        serializer = SignInSerializer(data=request.data)
        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            return response
        if request.user.is_authenticated:
            response = ApiErrorResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code=ApiErrorCodes.user_already_authorized,
                message="Пользователь уже авторизован"
            )
            return response
        validated_data = serializer.validated_data
        user: User = authenticate(request, username=validated_data['email'], password=validated_data['password'])
        if user is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code=ApiErrorCodes.bad_credentials,
                message="Неверные учетные данные"
            )
            return response
        login(request, user)
        response = ApiResponse(status_code=status.HTTP_200_OK,
                               message="Успешная авторизация")
        return response

    @action(detail=False, methods=['post'])
    @swagger_auto_schema(
        operation_summary='Регистрация нового пользователя',
        request_body=CreateUserSerializer,
        responses={201: None},
        tags=[
            'Аутентификация'
        ]
    )
    def signup(self, request: Request):
        serializer = CreateUserSerializer(data=request.data)
        if not serializer.is_valid():
            if User.objects.filter(email=serializer.data['email']):
                response = ApiErrorResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    error_code=ApiErrorCodes.user_already_exist,
                    message="Пользователь с таким email уже зарегистрирован"
                )
                return response
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            return response
        user = User.objects.create_user(
            email=serializer.validated_data['email'],
            phone=serializer.validated_data['phone'],
            company_name=serializer.validated_data['company_name'],
            company_address=serializer.validated_data['company_address'],
            password=serializer.validated_data['password'],
            middle_name=serializer.validated_data['middle_name'],
            first_name=serializer.validated_data['first_name'],
            last_name=serializer.validated_data['last_name'],
            position=serializer.validated_data['position'],
            is_active=True,
        )
        confirm_key = ActionKey.objects.create_key(user.email, ActionEnum.confirm)
        confirm_key.save()
        confirm_link = f'{settings.SITE_BASE_URL}/account-confirm?confirm_key={confirm_key.key}'
        send_mail(
            subject=f'{settings.APP_NAME} | Регистрация',
            message=f'Для завершения регистрации перейдите по ссылке',
            html_message=f'Для завершения регистрации перейдите по <a href="{confirm_link}">ссылке</a>',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[serializer.validated_data['email']]
        )
        response = ApiResponse(status_code=status.HTTP_201_CREATED,
                               message="Аккаунт успешно создан. На указаный email отправлено письмо"
                                       " для дальнейшего подтверждения аккаунта")
        return response

    @action(detail=False, methods=['post'])
    @swagger_auto_schema(
        operation_summary='Отправка на почту письма с ссылкой на восстановление пароля',
        request_body=ForgotUserSerializer,
        responses={201: None},
        tags=[
            'Аутентификация'
        ]
    )
    def forgot(self, request: Request):
        serializer = ForgotUserSerializer(data=request.data)
        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            return response
        user = User.objects.filter(email=serializer.validated_data['email']).first()
        if not user:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.user_not_found,
                message="Пользователь не найден"
            )
            return response

        restore_key = ActionKey.objects.create_key(email=user.email, action=ActionEnum.restore)
        restore_link = f'{settings.SITE_BASE_URL}/reset-password?restore_key={restore_key.key}'
        send_mail(
            subject=f'{settings.APP_NAME} | Восстановление пароля',
            message=f'Для установки нового пароля перейдите по ссылке',
            html_message=f'Для установки нового пароля перейдите по <a href="{restore_link}">ссылке</a>',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email]
        )
        response = ApiResponse(
            status_code=status.HTTP_200_OK,
            message="На ваш email отправлена инструкция по смене пароля"
        )
        return response

    @action(detail=False, methods=['post'])
    @swagger_auto_schema(
        operation_summary='Сброс пароля',
        request_body=RestorePasswordSerializer,
        responses={201: None},
        tags=[
            'Аутентификация'
        ]
    )
    def restore(self, request: Request):
        serializer = RestorePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            return response
        restore_key: ActionKey = ActionKey.objects.filter(key=serializer.validated_data['restore_key']).first()

        if not restore_key:
            return ApiErrorResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code=ApiErrorCodes.bad_restore_key,
                message="Неверный ключ сброса пароля"
            )
        restore_key.user.set_password(serializer.validated_data['password'])
        restore_key.user.save()
        restore_key.delete()
        response = ApiResponse(
            status_code=status.HTTP_200_OK,
            message="Пароль успешно изменен"
        )
        return response

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    @swagger_auto_schema(
        operation_summary='Изменение пароля (для авторизованого пользователя)',
        request_body=ChangePasswordSerializer,
        responses={201: None},
        tags=[
            'Аутентификация'
        ]
    )
    def change(self, request: Request):
        user = request.user
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            return response
        if user.check_password(serializer.validated_data['current_password']):
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            response = ApiResponse(
                status_code=status.HTTP_200_OK,
                message="Пароль успешно изменен"
            )
            info(request.path, request.data, response.data)
            return response
        response = ApiErrorResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ApiErrorCodes.bad_credentials,
            message="Неверные учетные данные"
        )
        return response

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    @swagger_auto_schema(
        operation_summary='Активация(подтверждение) зарегистрированного пользователя',
        responses={201: None},
        manual_parameters=[
            Parameter(
                name='confirm_key',
                in_='query',
                description='Ключ подтверждения пользователя',
                required=True,
                type='char',
            )],
        tags=[
            'Аутентификация'
        ]
    )
    def confirm(self, request: Request):
        key = request.GET.get('confirm_key')
        confirm_key: ActionKey = ActionKey.objects.filter(key=key, action=ActionEnum.confirm).first()
        if confirm_key is None:
            return ApiErrorResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code=ApiErrorCodes.bad_confirm_key,
                message=f'Неизвестный ключ {key}',
            )
        user = confirm_key.user
        user.is_confirmed = True
        user.save()
        confirm_key.delete()
        return HttpResponseRedirect(f'{settings.SITE_BASE_URL}/')

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    @swagger_auto_schema(
        operation_summary='Логаут пользователя',
        responses={200: None},
        tags=[
            'Аутентификация'
        ]
    )
    def logout(self, request: Request):
        logout(request)
        return ApiResponse()

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    @swagger_auto_schema(
        operation_summary='Повторная отправка сообщения о подтверждении аккаунта',
        responses={200: None},
        manual_parameters=[
            Parameter(
                name='confirm_key',
                in_='query',
                description='Ключ подтверждения пользователя',
                required=True,
                type='char',
            )],
        tags=[
            'Аутентификация'
        ]
    )
    def confirm_retry(self, request: Request):
        user = request.user
        now = timezone.now()
        confirm_key: ActionKey = ActionKey.objects.filter(user=user, action=ActionEnum.confirm).first()
        if confirm_key is not None:
            if now < confirm_key.created_at + timedelta(minutes=3):
                return ApiErrorResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code=ApiErrorCodes.send_confirm_email_limit,
                    message="Повторная отправка станет досутпна в течении 3х минут, пожалуйста, подождите"
                )

        confirm_key = ActionKey.objects.create_key(user.email, ActionEnum.confirm)
        confirm_key.save()
        confirm_link = f'{settings.SITE_BASE_URL}/account-confirm?confirm_key={confirm_key.key}'
        send_mail(
            subject=f'{settings.APP_NAME} | Подтверждение аккаунт',
            message=f'Для завершения регистрации перейдите по ссылке',
            html_message=f'Для завершения регистрации перейдите по <a href="{confirm_link}">ссылке</a>',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email]
        )
        response = ApiResponse(status_code=status.HTTP_201_CREATED,
                               message="На указаный email отправлено письмо для дальнейшего подтверждения аккаунта")
        return response
