from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return Response(
            {"detail": "خطای داخلی سرور.", "errors": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    detail = response.data
    if isinstance(detail, dict) and "detail" in detail and len(detail) == 1:
        payload = {"detail": detail["detail"]}
    else:
        payload = {"detail": "خطای اعتبارسنجی.", "errors": detail}
    response.data = payload
    return response