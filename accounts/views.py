"""
Views for user authentication and profile management.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.db.models import Count, Q
from django.core.paginator import Paginator

from core.models import Game, UserProgress


def register_view(request):
    """User registration view."""
    if request.user.is_authenticated:
        return redirect('lessons:lesson_list')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('lessons:lesson_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserCreationForm()

    context = {'form': form}
    return render(request, 'accounts/register.html', context)


def login_view(request):
    """User login view."""
    if request.user.is_authenticated:
        return redirect('lessons:lesson_list')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                next_url = request.GET.get('next', 'lessons:lesson_list')
                return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()

    context = {'form': form}
    return render(request, 'accounts/login.html', context)


def logout_view(request):
    """User logout view."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required
def profile_view(request):
    """User profile view with game history and progress."""
    user = request.user

    # Get game statistics
    total_games = Game.objects.filter(
        Q(white_player=user) | Q(black_player=user)
    ).count()

    completed_games = Game.objects.filter(
        Q(white_player=user) | Q(black_player=user),
        status='completed'
    ).count()

    games_as_white = Game.objects.filter(white_player=user).count()
    games_as_black = Game.objects.filter(black_player=user).count()

    # Get recent games with pagination
    recent_games_queryset = Game.objects.filter(
        Q(white_player=user) | Q(black_player=user)
    ).select_related('white_player', 'black_player').order_by('-created_at')

    # Pagination for recent games
    games_paginator = Paginator(recent_games_queryset, 5)  # Show 5 games per page on profile
    games_page_number = request.GET.get('games_page')
    recent_games = games_paginator.get_page(games_page_number)

    # Get learning progress
    progress_data = UserProgress.objects.filter(
        user=user
    ).select_related('lesson').annotate(
        completed_count=Count('completed_positions')
    ).order_by('lesson__order')

    # Calculate overall stats
    total_completed = sum(p.completed_positions.count() for p in progress_data)

    context = {
        'total_games': total_games,
        'completed_games': completed_games,
        'games_as_white': games_as_white,
        'games_as_black': games_as_black,
        'recent_games': recent_games,
        'progress_data': progress_data,
        'total_completed': total_completed,
    }
    return render(request, 'accounts/profile.html', context)
