"""
Views for the lessons app.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Count, Prefetch
import json

from core.models import Lesson, Topic, Position, PositionSequence, UserProgress, Game
from core.chess_engine import ChessEngine


@login_required
def lesson_list(request):
    """Display list of all lessons with progress."""
    # Teachers see all lessons, students only see enabled ones
    lessons = Lesson.objects.annotate(
        topics_count=Count('topics')
    ).prefetch_related('topics')

    if not request.user.is_staff:
        lessons = lessons.filter(is_enabled=True)

    # Get user progress for each lesson
    user_progress = {}
    for lesson in lessons:
        progress, _ = UserProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson
        )
        user_progress[lesson.id] = progress.get_completion_percentage()

    context = {
        'lessons': lessons,
        'user_progress': user_progress,
    }
    return render(request, 'lessons/lesson_list.html', context)


@login_required
def lesson_detail(request, lesson_id):
    """Display a specific lesson with its topics."""
    # Build topic queryset - teachers see all, students only enabled
    topic_queryset = Topic.objects.annotate(
        positions_count=Count('positions')
    )
    if not request.user.is_staff:
        topic_queryset = topic_queryset.filter(is_enabled=True)

    lesson = get_object_or_404(
        Lesson.objects.prefetch_related(
            Prefetch('topics', queryset=topic_queryset)
        ),
        id=lesson_id
    )

    # Get or create user progress
    progress, _ = UserProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson
    )

    context = {
        'lesson': lesson,
        'progress': progress,
        'completion_percentage': progress.get_completion_percentage(),
    }
    return render(request, 'lessons/lesson_detail.html', context)


@login_required
def topic_detail(request, topic_id):
    """Display a specific topic with its positions."""
    topic = get_object_or_404(
        Topic.objects.select_related('lesson').prefetch_related(
            'positions__sequences'
        ),
        id=topic_id
    )

    # Teachers see all positions, students only enabled ones
    positions = topic.positions.all()
    if not request.user.is_staff:
        positions = positions.filter(is_enabled=True)
    positions = positions.order_by('order')

    # Get user progress
    progress, _ = UserProgress.objects.get_or_create(
        user=request.user,
        lesson=topic.lesson
    )

    # Check which positions are completed
    completed_positions = progress.completed_positions.values_list('id', flat=True)

    context = {
        'topic': topic,
        'positions': positions,
        'completed_positions': list(completed_positions),
        'progress': progress,
    }
    return render(request, 'lessons/topic_detail.html', context)


@login_required
def position_viewer(request, position_id):
    """Display a specific position with navigation."""
    position = get_object_or_404(
        Position.objects.select_related('topic__lesson').prefetch_related(
            'sequences'
        ),
        id=position_id
    )

    # Get adjacent positions - teachers see all, students only enabled
    topic_positions = Position.objects.filter(
        topic=position.topic
    )
    if not request.user.is_staff:
        topic_positions = topic_positions.filter(is_enabled=True)
    topic_positions = topic_positions.order_by('order')

    position_list = list(topic_positions.values_list('id', flat=True))
    current_index = position_list.index(position.id)

    prev_position_id = position_list[current_index - 1] if current_index > 0 else None
    next_position_id = position_list[current_index + 1] if current_index < len(position_list) - 1 else None

    # Get sequences if this is a sequence position
    if position.is_sequence_part:
        sequences = position.sequences.all().order_by('sequence_order')
        # Include parent_move and variation_number for tree structure
        sequences_json = json.dumps([
            {
                'id': seq.id,
                'sequence_order': seq.sequence_order,
                'move_san': seq.move_san,
                'explanation': seq.explanation,
                'parent_move_id': seq.parent_move.id if seq.parent_move else None,
                'variation_number': seq.variation_number
            }
            for seq in sequences
        ])
    else:
        sequences = []
        sequences_json = '[]'

    # Get user progress
    progress, _ = UserProgress.objects.get_or_create(
        user=request.user,
        lesson=position.topic.lesson
    )

    is_completed = progress.completed_positions.filter(id=position.id).exists()

    context = {
        'position': position,
        'sequences': sequences,
        'sequences_json': sequences_json,
        'prev_position_id': prev_position_id,
        'next_position_id': next_position_id,
        'is_completed': is_completed,
        'progress': progress,
    }
    return render(request, 'lessons/position_viewer.html', context)


@login_required
@require_http_methods(["POST"])
def mark_position_complete(request, position_id):
    """Mark a position as completed."""
    try:
        position = get_object_or_404(Position, id=position_id)

        with transaction.atomic():
            progress, _ = UserProgress.objects.get_or_create(
                user=request.user,
                lesson=position.topic.lesson
            )
            progress.completed_positions.add(position)

        return JsonResponse({
            'success': True,
            'completion_percentage': progress.get_completion_percentage(),
            'message': 'Position marked as complete'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def practice_from_position(request, position_id):
    """Create a practice game from a specific position."""
    try:
        position = get_object_or_404(Position, id=position_id)

        # Parse request body for color and current FEN
        data = json.loads(request.body)
        user_color = data.get('color', 'white').lower()
        current_fen = data.get('current_fen', position.fen)

        # Validate color
        if user_color not in ['white', 'black']:
            return JsonResponse({
                'success': False,
                'message': 'Invalid color selection'
            }, status=400)

        # Validate FEN
        engine = ChessEngine()
        if not engine.is_valid_fen(current_fen):
            return JsonResponse({
                'success': False,
                'message': 'Invalid FEN position'
            }, status=400)

        # Create game with user assigned to chosen color
        with transaction.atomic():
            # Extract turn from FEN (second component)
            fen_parts = current_fen.split(' ')
            turn_indicator = fen_parts[1] if len(fen_parts) > 1 else 'w'
            current_turn = 'white' if turn_indicator == 'w' else 'black'

            game_data = {
                'position_fen': current_fen,
                'current_fen': current_fen,
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
            'message': 'Practice game created'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
def user_progress_view(request):
    """Display user's overall progress across all lessons."""
    progress_data = UserProgress.objects.filter(
        user=request.user
    ).select_related('lesson').prefetch_related(
        'completed_positions'
    ).order_by('lesson__order')

    # Calculate overall stats - teachers see all, students only enabled
    if request.user.is_staff:
        total_lessons = Lesson.objects.count()
        total_positions = Position.objects.count()
    else:
        total_lessons = Lesson.objects.filter(is_enabled=True).count()
        total_positions = Position.objects.filter(is_enabled=True).count()

    lessons_in_progress = progress_data.count()
    completed_positions = sum(p.completed_positions.count() for p in progress_data)

    overall_percentage = int((completed_positions / total_positions * 100)) if total_positions > 0 else 0

    context = {
        'progress_data': progress_data,
        'total_lessons': total_lessons,
        'lessons_in_progress': lessons_in_progress,
        'total_positions': total_positions,
        'completed_positions': completed_positions,
        'overall_percentage': overall_percentage,
    }
    return render(request, 'lessons/user_progress.html', context)
