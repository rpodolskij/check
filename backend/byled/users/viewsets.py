import uuid
import base64
from django.core.files.base import ContentFile

from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework import status

from byled.responses import ApiResponse, ApiErrorResponse, ApiErrorCodes
from authentication.utils import CsrfExemptBasicAuthentication

from django.shortcuts import get_object_or_404
from .models import User

from .serializers import UserSerializer, UserUpdateSerializer, ChangePasswordSerializer

from authentication.serializers import CreateUserSerializer
from utils.logging.logger import info, warning
from django.core.paginator import Paginator
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg.openapi import Parameter


class UserViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CsrfExemptBasicAuthentication, ]

    @swagger_auto_schema(
        operation_summary='Получить список пользователей',
        manual_parameters=[
            Parameter(
                name='account_type',
                in_='query',
                description="Тип аккаунта пользователей. Если не указан, возвращаются пользователи со всеми типами аккаунтов.\n"
                            "Допустимые значения:'CLIENT', 'MANAGER','ADMIN'",
                required=False,
                type='char',
            ),
            Parameter(
                name='offset',
                in_='query',
                description='Смещение от начала списка',
                required=False,
                type='int',
                default=0,
            ),
            Parameter(
                name='limit',
                in_='query',
                description='Количество элементов которое нужно вернуть',
                required=False,
                type='int',
            ),
            Parameter(
                name='query',
                in_='query',
                description='Поиск по названию',
                required=False,
                type='str',
            ),
            Parameter(
                name='sort',
                in_='query',
                description="Поле сортировки.\nCписок допустимых полей:\n'is_confirmed', '-is_confirmed', 'price_level', '-price_level',\
                        'first_name', '-first_name', 'last_name', '-last_name', 'middle_name', '-middle_name',\
                        'company_name', '-company_name', 'manager__first_name', '-manager__first_name'\
                        'manager__last_name', '-manager__last_name', 'manager__middle_name', '-manager__middle_name'\
                        'date_joined', '-date_joined'.\n <допустимое поле>: сортировка по возрастанию.\n <-допустимое поле>: сортировка по убыванию",
                required=False,
                type='str',
            )],
        tags=[
            'Пользователи'
        ]
    )
    def list(self, request: Request):
        account_type_filter = self.request.query_params.get('account_type')
        account_types = account_type_filter.upper().split(',') if account_type_filter else ['CLIENT', 'MANAGER',
                                                                                            'ADMIN']
        users_limit = self.request.query_params.get('limit')
        query = self.request.query_params.get('query')
        users_qs = User.objects.all()
        if request.user.account_type == 'MANAGER':
            users_qs = users_qs.filter(manager=request.user)
        users_qs = users_qs.filter(account_type__in=account_types)

        if 'sort' in request.query_params:
            sort = self.request.query_params.get('sort')
            if sort in {'is_confirmed', '-is_confirmed', 'price_level', '-price_level',
                        'first_name', '-first_name', 'last_name', '-last_name', 'middle_name', '-middle_name',
                        'company_name', '-company_name', 'manager__first_name', '-manager__first_name'
                                                                                'manager__last_name',
                        '-manager__last_name', 'manager__middle_name', '-manager__middle_name'
                                                                       'date_joined', '-date_joined'}:
                users_qs = users_qs.order_by(sort)

        total_count = users_qs.count()

        if query is not None:
            users_qs = users_qs.filter(Q(first_name__icontains=query) |
                                       Q(middle_name__icontains=query) |
                                       Q(last_name__icontains=query) |
                                       Q(company_name__icontains=query))

        if 'offset' in request.query_params:
            offset = int(self.request.query_params.get('offset'))
        else:
            offset = 0

        users_qs = users_qs[offset:]
        if users_limit is not None:
            paginator = Paginator(users_qs, users_limit)
            current_page = paginator.get_page(1)
        else:
            current_page = users_qs
        serializer = UserSerializer(current_page, many=True)
        result = ({'total_count': total_count, 'items': serializer.data})

        response = ApiResponse(result=result)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Получить данные любого профиля(только для Менеджеров и Клиентов)',
        tags=[
            'Пользователи'
        ]
    )
    def retrieve(self, request: Request, pk=None):
        current_user = request.user
        # if current_user.account_type == 'CLIENT':
        #     response = ApiErrorResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         error_code=ApiErrorCodes.bad_credentials,
        #         message="У вас недостаточно прав для выполнения данного действия"
        #     )
        #     warning(request.path, request.data, response.data)
        #     return response
        users_qs = User.objects.all()
        user = get_object_or_404(users_qs, pk=pk)
        serializer = UserSerializer(user)
        response = ApiResponse(result=serializer.data)
        return response

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    @swagger_auto_schema(
        operation_summary='Получить данные профиля(свои, доступен только авторизованному пользователю)',
        tags=[
            'Пользователи'
        ]
    )
    def me(self, request: Request):
        user = request.user
        serializer = UserSerializer(user)
        response = ApiResponse(result=serializer.data)
        info(request.path, request.data, response.data)
        return response

    @swagger_auto_schema(
        operation_summary='Изменение пользователя (менеджеры могут менять клиентов, админы всех, клиенты никого)',
        request_body=UserUpdateSerializer,
        responses={201: None},
        tags=[
            'Пользователи'
        ]
    )
    def update(self, request: Request, pk=None):
        current_user = request.user
        user = User.objects.filter(id=pk).first()
        if user is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.user_not_found,
                message="Пользователь не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        if (current_user.account_type == 'CLIENT') and (current_user != user):
            response = ApiErrorResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code=ApiErrorCodes.bad_credentials,
                message="У вас недостаточно прав для выполнения данного действия"
            )
            warning(request.path, request.data, response.data)
            return response
        if current_user.account_type == 'MANAGER':
            if (user.account_type != 'CLIENT') and (current_user != user):
                response = ApiErrorResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    error_code=ApiErrorCodes.bad_credentials,
                    message="У вас недостаточно прав для выполнения данного действия"
                )
                warning(request.path, request.data, response.data)
                return response

        serializer = UserUpdateSerializer(user, data=request.data)

        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            warning(request.path, request.data, response.data)
            return response

        serializer.save()

        return ApiResponse(message=f'Данные успешно обновлены', result=UserSerializer(user).data)

    @swagger_auto_schema(
        operation_summary='Создание пользователя админом (не самостоятельная регистрация)',
        request_body=CreateUserSerializer,
        responses={201: None},
        tags=[
            'Пользователи'
        ]
    )
    def create(self, request: Request):
        serializer = CreateUserSerializer(data=request.data)
        if not serializer.is_valid():
            resp = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            warning(request.path, request.data, resp.data)
            return resp
        User.objects.create_user(email=serializer.validated_data['email'],
                                 password=serializer.validated_data['password'],
                                 middle_name=serializer.validated_data['middle_name'],
                                 phone=serializer.validated_data['phone'],
                                 company_name=serializer.validated_data['company_name'],
                                 company_address=serializer.validated_data['company_address'],
                                 position=serializer.validated_data['position'])

        response = ApiResponse(status_code=status.HTTP_201_CREATED,
                               message="Успешное добавление клиента")
        info(request.path, request.data, response.data)
        return response

    @action(methods=['post'], url_path='upload', detail=True)
    @swagger_auto_schema(
        operation_summary='Добавление пользователю картинки(аватара)',
        tags=[
            'Пользователи'
        ]
    )
    def upload(self, request: Request, pk=None):
        user = User.objects.filter(id=pk).first()
        if user is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.user_not_found,
                message="Пользователь не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        image_data = request.data.get('image')
        if image_data is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.file_not_found,
                message="Файл не найден",
            )
            warning(request.path, request.data, response.data)
            return response

        media_format, image_base64 = image_data.split(';base64,')

        ext = media_format.split('/')[-1]
        filename = f'{str(uuid.uuid4())}.{ext}'
        image: ContentFile = ContentFile(base64.b64decode(image_base64))
        user.avatar.save(filename, image, save=True)

        response = ApiResponse(message=f'Изображение успешно обновлено', result=UserSerializer(user).data)
        info(request.path, request.data, response.data)
        return response

    @action(methods=['get'], url_path='activate', detail=True, permission_classes=[IsAuthenticated])
    @swagger_auto_schema(
        operation_summary='Активация пользователя админом',
        tags=[
            'Пользователи'
        ]
    )
    def activate(self, request: Request, pk=None):
        current_user = request.user
        user = User.objects.filter(id=pk).first()
        if user is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.user_not_found,
                message="Пользователь не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        if current_user.account_type == 'CLIENT':
            response = ApiErrorResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code=ApiErrorCodes.bad_credentials,
                message="У вас недостаточно прав для выполнения данного действия"
            )
            warning(request.path, request.data, response.data)
            return response
        if current_user.account_type == 'MANAGER':
            if user.account_type != 'CLIENT':
                response = ApiErrorResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    error_code=ApiErrorCodes.bad_credentials,
                    message="У вас недостаточно прав для выполнения данного действия"
                )
                warning(request.path, request.data, response.data)
                return response
        user.is_active = True
        user.save()
        response = ApiResponse(message=f'Аккаунт {user.first_name} {user.last_name} активирован',
                               status_code=status.HTTP_200_OK, )
        info(request.path, request.data, response.data)
        return response

    @action(methods=['post'], url_path='set_role', detail=True, permission_classes=[IsAdminUser])
    @swagger_auto_schema(
        operation_summary='Назначать роль для пользователя',
        manual_parameters=[
            Parameter(
                name='account_type',
                in_='query',
                description='Роль аккаунта',
                required=True,
                type='string',
            ),

        ],
        tags=[
            'Пользователи'
        ]
    )
    def set_role(self, request: Request, pk=None):
        current_user = request.user
        user = User.objects.filter(id=pk).first()
        account_type = request.query_params.get('account_type')
        if user is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.user_not_found,
                message="Пользователь не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        if current_user.account_type != 'ADMIN':
            response = ApiErrorResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code=ApiErrorCodes.bad_credentials,
                message="У вас недостаточно прав для выполнения данного действия"
            )
            warning(request.path, request.data, response.data)
            return response

        user.account_type = account_type
        user.save()
        response = ApiResponse(message=f'Аккаунт {user.first_name} {user.last_name} назначен на роль {account_type}',
                               status_code=status.HTTP_200_OK)
        info(request.path, request.data, response.data)
        return response

    @action(methods=['get'], url_path='deactivate', permission_classes=[IsAuthenticated], detail=True)
    @swagger_auto_schema(
        operation_summary='Деактивация пользователя админом',
        tags=[
            'Пользователи'
        ]
    )
    def deactivate(self, request: Request, pk=None):
        current_user = request.user
        user = User.objects.filter(id=pk).first()
        if user is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.user_not_found,
                message="Пользователь не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        if current_user.account_type == 'CLIENT':
            response = ApiErrorResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code=ApiErrorCodes.bad_credentials,
                message="У вас недостаточно прав для выполнения данного действия"
            )
            warning(request.path, request.data, response.data)
            return response
        if current_user.account_type == 'MANAGER':
            if user.account_type != 'CLIENT':
                response = ApiErrorResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    error_code=ApiErrorCodes.bad_credentials,
                    message="У вас недостаточно прав для выполнения данного действия"
                )
                warning(request.path, request.data, response.data)
                return response
        user.is_active = False
        user.save()
        return ApiResponse(message=f'Аккаунт {user.first_name} {user.last_name} деактивирован')

    @swagger_auto_schema(
        operation_summary='Удаление пользователя админом (админ может удалять всех, менеджер - клиентов, клиент - никого',
        tags=[
            'Пользователи'
        ]
    )
    def destroy(self, request: Request, pk=None):
        current_user = request.user
        user = User.objects.filter(id=pk).first()
        if user is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.user_not_found,
                message="Пользователь не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        if current_user.account_type == 'CLIENT':
            response = ApiErrorResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code=ApiErrorCodes.bad_credentials,
                message="У вас недостаточно прав для выполнения данного действия"
            )
            warning(request.path, request.data, response.data)
            return response
        if current_user.account_type == 'MANAGER':
            if user.account_type != 'CLIENT':
                response = ApiErrorResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    error_code=ApiErrorCodes.bad_credentials,
                    message="У вас недостаточно прав для выполнения данного действия"
                )
                warning(request.path, request.data, response.data)
                return response
        user.delete()
        response = ApiResponse(status_code=status.HTTP_200_OK,
                               message=f'Аккаунт с id={pk} удален')
        info(request.path, request.data, response.data)
        return response

    @action(methods=['put'], url_path='change_password', permission_classes=[IsAuthenticated], detail=True)
    @swagger_auto_schema(
        operation_summary='Изменение пароля пользователю ',
        operation_description='(админ может менять всем, мэнеджер - клиентам, клиенты - никому',

        # request_body=ChangePasswordSerializer,
        tags=[
            'Пользователи'
        ]
    )
    def change_password(self, request: Request, pk=None):
        current_user = request.user
        user = User.objects.filter(id=pk).first()
        if user is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.user_not_found,
                message="Пользователь не найден",
            )
            warning(request.path, request.data, response.data)
            return response
        if current_user.account_type == 'CLIENT':
            response = ApiErrorResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code=ApiErrorCodes.bad_credentials,
                message="У вас недостаточно прав для выполнения данного действия"
            )
            warning(request.path, request.data, response.data)
            return response
        if current_user.account_type == 'MANAGER':
            if user.account_type != 'CLIENT':
                response = ApiErrorResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    error_code=ApiErrorCodes.bad_credentials,
                    message="У вас недостаточно прав для выполнения данного действия"
                )
                warning(request.path, request.data, response.data)
                return response

        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            info(request.path, request.data, response.data)
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
        info(request.path, request.data, response.data)
        return response
