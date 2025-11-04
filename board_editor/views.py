"""
Views for the board editor app.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
import json

from core.models import Game, Position, Topic
from core.chess_engine import ChessEngine


@login_required
def editor(request):
    """Display the chess board editor."""
    context = {
        'starting_fen': ChessEngine.get_starting_fen(),
    }
    return render(request, 'board_editor/editor.html', context)


@login_required
@require_http_methods(["POST"])
def validate_fen(request):
    """Validate a FEN string via AJAX."""
    try:
        data = json.loads(request.body)
        fen = data.get('fen', '')

        engine = ChessEngine()
        is_valid = engine.is_valid_fen(fen)

        if is_valid:
            engine.set_position(fen)
            return JsonResponse({
                'valid': True,
                'message': 'Valid FEN string',
                'turn': engine.get_current_turn(),
            })
        else:
            return JsonResponse({
                'valid': False,
                'message': 'Invalid FEN string'
            })

    except json.JSONDecodeError:
        return JsonResponse({
            'valid': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'valid': False,
            'message': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def generate_game_link(request):
    """Generate a shareable game link from a FEN position."""
    try:
        data = json.loads(request.body)
        fen = data.get('fen', '')
        user_color = data.get('color', 'white').lower()

        # Validate color
        if user_color not in ['white', 'black']:
            return JsonResponse({
                'success': False,
                'message': 'Invalid color selection'
            }, status=400)

        # Validate FEN
        engine = ChessEngine()
        if not engine.is_valid_fen(fen):
            return JsonResponse({
                'success': False,
                'message': 'Invalid FEN string'
            }, status=400)

        # Create game with user assigned to chosen color
        with transaction.atomic():
            # Extract turn from FEN (second component)
            fen_parts = fen.split(' ')
            turn_indicator = fen_parts[1] if len(fen_parts) > 1 else 'w'
            current_turn = 'white' if turn_indicator == 'w' else 'black'

            game_data = {
                'position_fen': fen,
                'current_fen': fen,
                'current_turn': current_turn,
                'status': 'waiting'
            }

            if user_color == 'white':
                game_data['white_player'] = request.user
            else:
                game_data['black_player'] = request.user

            game = Game.objects.create(**game_data)

        game_url = request.build_absolute_uri(f'/game/{game.unique_link}/')

        return JsonResponse({
            'success': True,
            'game_link': str(game.unique_link),
            'game_url': game_url,
            'message': 'Game link generated successfully'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def save_position_to_lesson(request):
    """Save a position to a lesson (admin only)."""
    if not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'message': 'Admin privileges required'
        }, status=403)

    try:
        data = json.loads(request.body)
        fen = data.get('fen', '')
        topic_id = data.get('topic_id')
        description = data.get('description', '')
        is_sequence_part = data.get('is_sequence_part', False)

        # Validate FEN
        engine = ChessEngine()
        if not engine.is_valid_fen(fen):
            return JsonResponse({
                'success': False,
                'message': 'Invalid FEN string'
            }, status=400)

        # Get topic
        try:
            topic = Topic.objects.get(id=topic_id)
        except Topic.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Topic not found'
            }, status=404)

        # Get the next order number
        max_order = Position.objects.filter(topic=topic).count()

        # Create position
        with transaction.atomic():
            position = Position.objects.create(
                topic=topic,
                fen=fen,
                description=description,
                order=max_order + 1,
                is_sequence_part=is_sequence_part
            )

        return JsonResponse({
            'success': True,
            'position_id': position.id,
            'message': 'Position saved successfully'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
def get_topics_list(request):
    """Get list of topics for dropdown (admin only)."""
    if not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'message': 'Admin privileges required'
        }, status=403)

    topics = Topic.objects.select_related('lesson').all().order_by(
        'lesson__order', 'order'
    )

    topics_data = [
        {
            'id': topic.id,
            'title': topic.title,
            'lesson_title': topic.lesson.title
        }
        for topic in topics
    ]

    return JsonResponse({
        'success': True,
        'topics': topics_data
    })
