from functools import wraps
from django.http import JsonResponse
import os

PP_TOKEN = os.getenv("PP_TOKEN")

def token_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if auth_header != PP_TOKEN:
            return JsonResponse({"error": "Forbidden"}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view