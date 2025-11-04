"""
Views for the gameplay app.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.core.paginator import Paginator

from core.models import Game, GameMove


@login_required
def game_view(request, game_id):
    """Display a live chess game."""
    game = get_object_or_404(
        Game.objects.select_related('white_player', 'black_player'),
        unique_link=game_id
    )

    # Determine player's color
    user_color = None
    if game.white_player == request.user:
        user_color = 'white'
    elif game.black_player == request.user:
        user_color = 'black'

    # Get move history
    moves = GameMove.objects.filter(game=game).order_by('move_number')

    context = {
        'game': game,
        'user_color': user_color,
        'moves': moves,
        'can_join': game.status == 'waiting' and user_color is None,
    }
    return render(request, 'gameplay/game.html', context)


@login_required
def game_list(request):
    """Display list of user's games."""
    # Get user's games
    games = Game.objects.filter(
        white_player=request.user
    ) | Game.objects.filter(
        black_player=request.user
    )

    games = games.select_related('white_player', 'black_player').order_by('-created_at')

    # Pagination
    paginator = Paginator(games, 10)  # Show 10 games per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'games': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'gameplay/game_list.html', context)


@login_required
@require_http_methods(["POST"])
def create_game(request):
    """Create a new game (quick play)."""
    try:
        from core.chess_engine import ChessEngine

        with transaction.atomic():
            game = Game.objects.create(
                position_fen=ChessEngine.get_starting_fen(),
                current_fen=ChessEngine.get_starting_fen(),
                white_player=request.user,
                status='waiting'
            )

        return redirect('gameplay:game_view', game_id=game.unique_link)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
