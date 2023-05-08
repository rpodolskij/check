from typing import Optional, Dict
from enum import IntEnum

from rest_framework.response import Response
from rest_framework import status


class ApiErrorCodes(IntEnum):
    # Общее
    validation = 1
    missing_parameters = 2

    # Авторизация
    bad_credentials = 101
    bad_restore_key = 102
    user_already_authorized = 103
    bad_confirm_key = 104
    send_confirm_email_limit = 105

    # Пользователи
    user_not_found = 201
    user_already_exist = 202

    # Файлы
    file_not_found = 301

    # Продукты
    product_not_found = 401
    order_not_found = 402
    order_item_not_found = 403

    # Проекты
    project_not_found = 601
    room_not_found = 602
    area_not_found = 603
    area_item_not_found = 604

    # Блог
    post_not_found = 701
    comment_not_found = 702
    category_not_found = 703


def ApiResponse(message: Optional[str] = None, result: Optional[Dict] = None, status_code: int = status.HTTP_200_OK):
    response_body = {
        'error': False,
    }
    if message is not None:
        response_body['message'] = message
    if result is not None:
        response_body['result'] = result
    return Response(data=response_body, status=status_code)


def ApiErrorResponse(status_code: int, error_code: ApiErrorCodes, message: str, result: Optional[Dict] = None):
    response_body = {
        'error': True,
        'errorCode': error_code,
        'message': message,
    }
    if result is not None:
        response_body['result'] = result
    return Response(data=response_body, status=status_code)
