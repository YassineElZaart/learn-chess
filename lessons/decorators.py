"""
Permission decorators for teacher-only access.
"""
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponseForbidden


def teacher_required(view_func):
    """
    Decorator to restrict access to teachers (is_staff users).

    Usage:
        @teacher_required
        def my_teacher_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this page.')
            return redirect(f'/accounts/login/?next={request.path}')

        if not request.user.is_staff:
            messages.error(request, 'You must be a teacher to access this page.')
            return HttpResponseForbidden('Teacher access required.')

        return view_func(request, *args, **kwargs)

    return wrapper
