import uuid
import os

from PIL import Image
from django.conf import settings

from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status

from drf_yasg.utils import swagger_auto_schema

from byled.responses import ApiResponse, ApiErrorResponse, ApiErrorCodes
from authentication.utils import CsrfExemptBasicAuthentication

from .models import File
from .serializers import FileSerializer


# Create your views here.


class FileViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CsrfExemptBasicAuthentication, ]

    @swagger_auto_schema(
        operation_summary='Загрузка файла',

        tags=[
            'Файлы'
        ]
    )
    def create(self, request: Request):

        file_data = request.data.get('file')
        if file_data is None:
            response = ApiErrorResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ApiErrorCodes.file_not_found,
                message="Файл не передан",
            )
            return response

        ext = str(file_data).split('.')[-1]
        name = str(uuid.uuid4())
        filename = f'{name}.{ext}'
        filepath = os.path.join(settings.MEDIA_ROOT, filename)

        with open(f'{filepath}', 'wb+') as destination:
            for chunk in file_data.chunks():
                destination.write(chunk)

        thumbnail_path = os.path.join(settings.MEDIA_ROOT, f'{name}-thumbnail.png')
        image = Image.open(filepath)
        image = image.convert('RGBA')
        dest_width = 200
        multiplier = image.size[0] / dest_width
        dest_height = image.size[1] / multiplier
        image = image.resize(
            (round(dest_width), round(dest_height)),
            Image.ANTIALIAS,
        )
        image.save(thumbnail_path)

        # dest_path = os.path.join(settings.PRODUCTS_IMAGES_DIR, f'{id}.png')
        # src_path = f'{settings.ONE_C_TEMP_DIR}/images/{images_filenames[short_images_filenames.index(id)]}'
        # thumbnail_path = os.path.join(settings.PRODUCTS_IMAGES_DIR, f'{id}-thumbnail.png')
        # if not os.path.exists(dest_path):
        #     image = Image.open(src_path)
        #     image = image.convert('RGBA')
        #     image.save(dest_path)
        # if not os.path.exists(thumbnail_path):
        #     image = Image.open(src_path)
        #     image = image.convert('RGBA')
        #     dest_width = 200
        #     multiplier = image.size[0] / dest_width
        #     dest_height = image.size[1] / multiplier
        #     image = image.resize(
        #         (round(dest_width), round(dest_height)),
        #         Image.ANTIALIAS,
        #     )
        #     image.save(thumbnail_path)

        file = File(
            name=str(file_data),
            ext=ext,
            path=filename,

        )
        file.save()
        response = ApiResponse(message=f'Файл успешно загружен', result=FileSerializer(file).data)
        return response
