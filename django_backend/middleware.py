"""Small middleware to disable CSRF checks for API endpoints during local dev.

This sets request._dont_enforce_csrf_checks = True for requests starting with /api/.
Only intended for local development convenience; remove or tighten for production.
"""
from typing import Callable


class DisableCsrfForApiMiddleware:
    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        try:
            path = request.path
        except Exception:
            path = ''
        if path.startswith('/api/'):
            # instruct CsrfViewMiddleware to skip checks for this request
            setattr(request, '_dont_enforce_csrf_checks', True)
        return self.get_response(request)
