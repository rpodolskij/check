from rest_framework import viewsets, status
from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from byled.responses import ApiErrorCodes, ApiResponse, ApiErrorResponse
from .models import Post, Comment, Categories
from .serializers import PostSerializer, CommentSerializer, CategoriesSerializer, \
    PostCreateUpdateSerializer, CategoriesCreateUpdateSerializer, CommentCreateSerializer
from utils.logging.logger import info, warning
from django.core.paginator import Paginator
from authentication.utils import CsrfExemptBasicAuthentication
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg.openapi import Parameter
import uuid
import base64
from django.core.files.base import ContentFile
from django.utils.timezone import get_current_timezone
from datetime import datetime


class PostViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CsrfExemptBasicAuthentication, ]

    def parse_filter(self, value):
        field_filter = value
        if field_filter and (type(field_filter) == str):
            field_filter = field_filter.split(',')
        return field_filter

    @swagger_auto_schema(
        operation_summary='Создание нового поста(без картинки, картинка добавляется отдельно)',
        request_body=PostCreateUpdateSerializer,
        responses={201: None},
        tags=[
            'Посты'
        ]
    )
    def create(self, request: Request):
        current_user = request.user
        serializer = PostCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            resp = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            return resp
        if current_user.account_type == 'CLIENT':
            response = ApiErrorResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code=ApiErrorCodes.bad_credentials,
                message="У вас недостаточно прав для выполнения данного действия"
            )
            return response

        post = Post.objects.create(
            title=serializer.validated_data['title'],
            slug=serializer.validated_data['slug'],
            text=serializer.validated_data['text'],
            picture=serializer.validated_data['picture'],
            author=request.user,

            created_at=datetime.now(tz=get_current_timezone()),
        )
        if 'status' in serializer.validated_data:
            post.status = serializer.validated_data['status']
            post.save()
        if 'categories' in serializer.validated_data:
            categories = serializer.validated_data['categories']
            if categories is not None:
                for category in categories:
                    post.categories.add(category)
                post.save()

        response = ApiResponse(status_code=status.HTTP_201_CREATED,
                               message="Ваш пост успешно добавлен",
                               result=PostSerializer(post).data)
        return response

    @swagger_auto_schema(
        operation_summary='Загрузка картинки к посту',
        manual_parameters=[
            Parameter(
                name='image',
                in_='query',
                description='собственно сама картинка',
                required=True,
                type='file',
            )],
        responses={},
        tags=[
            'Посты'
        ]
    )
    @action(methods=['post'], url_path='upload', detail=True)
    def upload(self, request: Request, pk=None):
        post = Post.objects.filter(id=pk).first()
        if post is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.post_not_found,
                message=f"Пост c id={pk} не найден",
            )
            return response
        image_data = request.data.get('image')
        if image_data is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.file_not_found,
                message="Файл не найден",
            )
            return response

        media_format, image_base64 = image_data.split(';base64,')

        ext = media_format.split('/')[-1]
        filename = f'{str(uuid.uuid4())}.{ext}'
        image: ContentFile = ContentFile(base64.b64decode(image_base64))
        post.picture.save(filename, image, save=True)

        response = ApiResponse(message=f'Изображение успешно обновлено', result=PostSerializer(post).data)
        return response

    @swagger_auto_schema(
        operation_summary='Обновление полей поста(можно частично)',
        request_body=PostCreateUpdateSerializer,
        responses={},
        tags=[
            'Посты'
        ]
    )
    def update(self, request: Request, pk=None):
        post = Post.objects.filter(id=pk).first()
        current_user = request.user

        if post is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.user_not_found,
                message=f"Пост c id={pk} не найден",
            )
            return response
        if current_user.account_type == 'CLIENT':
            response = ApiErrorResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code=ApiErrorCodes.bad_credentials,
                message="У вас недостаточно прав для выполнения данного действия"
            )
            return response

        serializer = PostCreateUpdateSerializer(post, data=request.data, partial=True)

        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            return response

        serializer.save()
        response = ApiResponse(message=f'Данные успешно обновлены', result=PostSerializer(post).data)
        return response

    @swagger_auto_schema(
        operation_summary='Удаление поста админом или менеджером',
        tags=[
            'Посты'
        ]
    )
    def destroy(self, request: Request, pk=None):
        current_user = request.user
        post = Post.objects.filter(id=pk).first()

        if post is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.post_not_found,
                message=f"Поcт с id={pk} не существует",
            )
            return response
        if current_user.account_type == 'CLIENT':
            response = ApiErrorResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code=ApiErrorCodes.bad_credentials,
                message="У вас недостаточно прав для выполнения данного действия"
            )
            return response

        response = ApiResponse(status_code=status.HTTP_200_OK,
                               message=f'Пост с id={pk} удален',
                               result=PostSerializer(post).data)
        post.delete()
        return response

    @swagger_auto_schema(
        operation_summary='Получение поста по id',
        tags=[
            'Посты'
        ]
    )
    def retrieve(self, request, pk=None):
        post = Post.objects.filter(id=pk).first()
        if post is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.post_not_found,
                message=f"Поcт c с id={pk} не существует",
            )
            return response
        serializer = PostSerializer(post, many=False)

        response = ApiResponse(result=serializer.data)
        return response

    @swagger_auto_schema(
        operation_summary='Получить список постов',
        manual_parameters=[
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
                description='Поиск по названию и тектсу поста',
                required=False,
                type='str',
            ),
            Parameter(
                name='category',
                in_='query',
                description='Id категории, можно указать несколько',
                required=False,
                type='int',
            ),
            Parameter(
                name='slug',
                in_='query',
                description='Поиск по слагу поста',
                required=False,
                type='str',
            ),

        ],
        responses={},
        tags=['Посты']
    )
    def list(self, request: Request):
        current_user = request.user
        category = self.parse_filter(self.request.query_params.get('category'))
        limit = (self.request.query_params.get('limit'))
        query = (self.request.query_params.get('query'))
        slug = (self.request.query_params.get('slug'))
        if current_user.account_type == 'CLIENT':
            posts_qs = Post.objects.filter(status='PUBLISHED')
        else:
            posts_qs = Post.objects.all()

        if category is not None:
            posts_qs = posts_qs.filter(categories__in=category).distinct()

        if slug is not None:
            posts_qs = posts_qs.filter(slug=slug)

        if query is not None:
            posts_qs = posts_qs.filter(Q(title__icontains=query) |
                                       Q(text__icontains=query))
        if 'offset' in request.query_params:
            offset = int(self.request.query_params.get('offset'))
        else:
            offset = 0
        posts_qs = posts_qs[offset:]
        if limit is not None:
            paginator = Paginator(posts_qs, limit)
            current_page = paginator.get_page(1)
        else:
            current_page = posts_qs

        serializer = PostSerializer(current_page, many=True)

        response = ApiResponse(result=serializer.data)
        return response


class CommentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CsrfExemptBasicAuthentication, ]

    @swagger_auto_schema(
        operation_summary='Добавление(создание) нового комментария',
        request_body=CommentCreateSerializer,
        responses={201: None},
        tags=[
            'Комментарии'
        ]
    )
    def create(self, request: Request, post_pk=None):
        current_user = request.user
        serializer = CommentCreateSerializer(data=request.data)
        post = Post.objects.filter(id=post_pk).first()
        if post is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.post_not_found,
                message=f"Пост c id={post_pk} не существует",
            )
            return response
        if not serializer.is_valid():
            resp = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            return resp

        comment = Comment.objects.create(text=serializer.validated_data['text'],
                                         post=post,
                                         user=current_user,
                                         created_at=datetime.now(tz=get_current_timezone())
                                         )
        response = ApiResponse(status_code=status.HTTP_201_CREATED,
                               message="Ваш комментарий успешно добавлен",
                               result=CommentSerializer(comment).data)
        return response

    @swagger_auto_schema(
        operation_summary='Удаление комментария(написавшим его пользователем или любым менеджером/админом',
        tags=[
            'Комментарии'
        ]
    )
    def destroy(self, request: Request, post_pk=None, pk=None):
        current_user = request.user
        comment = Comment.objects.filter(id=pk).first()
        post = Post.objects.filter(id=post_pk).first()
        if post is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.post_not_found,
                message=f"Пост c id={post_pk} не существует",
            )
            return response
        if comment is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.comment_not_found,
                message=f"Комментарий c id={pk} не существует",
            )
            return response
        if current_user.account_type == 'CLIENT' and comment.user != current_user:
            response = ApiErrorResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code=ApiErrorCodes.bad_credentials,
                message="У вас недостаточно прав для выполнения данного действия"
            )
            return response
        response = ApiResponse(status_code=status.HTTP_200_OK,
                               message=f'Комментарий с id={pk} удален',
                               result=CommentSerializer(comment).data)
        comment.delete()
        return response

    @swagger_auto_schema(
        operation_summary='Получить список комментариев',
        manual_parameters=[
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
            # '''
            # Parameter(
            #     name='user',
            #     in_='query',
            #     description='Id пользователя, чьи комментарии отображать',
            #     required=False,
            #     type='int',
            # ),
            # '''

        ],
        responses={},
        tags=['Комментарии']
    )
    def list(self, request: Request, post_pk=None):
        limit = (self.request.query_params.get('limit'))
        # user = self.request.query_params.get('user')
        post = Post.objects.filter(id=post_pk).first()
        if post is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.post_not_found,
                message=f"Пост c id={post_pk} не существует",
            )
            return response
        comments_qs = Comment.objects.filter(post=post)

        # if user is not None:
        # comments_qs = comments_qs.filter(user=user)
        if 'offset' in request.query_params:
            offset = int(self.request.query_params.get('offset'))
        else:
            offset = 0

        comments_qs = comments_qs[offset:]
        if limit is not None:
            paginator = Paginator(comments_qs, limit)
            current_page = paginator.get_page(1)
        else:
            current_page = comments_qs

        serializer = CommentSerializer(current_page, many=True)

        response = ApiResponse(result=serializer.data)
        return response


class CategoriesViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CsrfExemptBasicAuthentication, ]

    @swagger_auto_schema(
        operation_summary='Добавление(создание) новой категории',
        request_body=CategoriesCreateUpdateSerializer,
        responses={201: None},
        tags=[
            'Категории'
        ]
    )
    def create(self, request: Request):
        current_user = request.user
        serializer = CategoriesCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            resp = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            return resp
        if current_user.account_type == 'CLIENT':
            response = ApiErrorResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code=ApiErrorCodes.bad_credentials,
                message="У вас недостаточно прав для выполнения данного действия"
            )
            return response
        category = Categories.objects.create(
            title=serializer.validated_data['title'],
            created_at=datetime.now(tz=get_current_timezone()),
            picture=serializer.validated_data['picture'],
        )
        response = ApiResponse(status_code=status.HTTP_201_CREATED,
                               message="Ваша категория успешно добавлена",
                               result=CategoriesSerializer(category).data)
        return response

    @swagger_auto_schema(
        operation_summary='Обновление полей категории(можно частично)',
        request_body=CategoriesCreateUpdateSerializer,
        responses={201: None},
        tags=[
            'Категории'
        ]
    )
    def update(self, request: Request, pk=None):
        category = Categories.objects.filter(id=pk).first()
        current_user = request.user

        if category is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.user_not_found,
                message=f"Категория с id={pk} не найдена",
            )
            return response
        if current_user.account_type == 'CLIENT':
            response = ApiErrorResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code=ApiErrorCodes.bad_credentials,
                message="У вас недостаточно прав для выполнения данного действия"
            )
            return response

        serializer = CategoriesCreateUpdateSerializer(category, data=request.data, partial=True)

        if not serializer.is_valid():
            response = ApiErrorResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ApiErrorCodes.validation,
                message="Ошибка валидации",
                result=serializer.errors
            )
            return response

        serializer.save()
        response = ApiResponse(message=f'Данные успешно обновлены', result=CategoriesSerializer(category).data)
        return response

    @swagger_auto_schema(
        operation_summary='Удаление категории',
        tags=[
            'Категории'
        ]
    )
    def destroy(self, request: Request, pk=None):
        current_user = request.user
        category = Categories.objects.filter(id=pk).first()

        if category is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.user_not_found,
                message=f"Категория c id={pk} не существует",
            )
            return response
        if current_user.account_type == 'CLIENT':
            response = ApiErrorResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code=ApiErrorCodes.bad_credentials,
                message="У вас недостаточно прав для выполнения данного действия"
            )
            return response

        response = ApiResponse(status_code=status.HTTP_200_OK,
                               message=f'Категория с id={pk} удалена',
                               result=CategoriesSerializer(category).data)
        category.delete()
        return response

    @swagger_auto_schema(
        operation_summary='Получить список категорий',
        manual_parameters=[
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
                description='Поиск по названию категории',
                required=False,
                type='str',
            ),

        ],
        responses={},
        tags=['Категории']
    )
    def list(self, request: Request):
        limit = (self.request.query_params.get('limit'))

        query = (self.request.query_params.get('query'))
        categories_qs = Categories.objects.all()

        if query is not None:
            categories_qs = categories_qs.filter(title__icontains=query)
        if 'offset' in request.query_params:
            offset = int(self.request.query_params.get('offset'))
        else:
            offset = 0

        categories_qs = categories_qs[offset:]
        if limit is not None:
            paginator = Paginator(categories_qs, limit)
            current_page = paginator.get_page(1)
        else:
            current_page = categories_qs

        serializer = CategoriesSerializer(current_page, many=True)

        response = ApiResponse(result=serializer.data)
        return response
