"""
Teacher management views for lessons, topics, and positions.
"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from core.models import Lesson, Topic, Position, PositionSequence
from .forms import LessonForm, TopicForm, PositionForm
from .decorators import teacher_required


# Lesson Management Views

@teacher_required
def lesson_create(request):
    """Create a new lesson."""
    if request.method == 'POST':
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.created_by = request.user
            lesson.save()
            messages.success(request, f'Lesson "{lesson.title}" created successfully!')
            return redirect('lessons:lesson_list')
    else:
        form = LessonForm()

    return render(request, 'lessons/lesson_form.html', {
        'form': form,
        'action': 'Create',
        'cancel_url': 'lessons:lesson_list'
    })


@teacher_required
def lesson_update(request, pk):
    """Update an existing lesson."""
    lesson = get_object_or_404(Lesson, pk=pk)

    if request.method == 'POST':
        form = LessonForm(request.POST, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, f'Lesson "{lesson.title}" updated successfully!')
            return redirect('lessons:lesson_detail', lesson_id=lesson.pk)
    else:
        form = LessonForm(instance=lesson)

    return render(request, 'lessons/lesson_form.html', {
        'form': form,
        'action': 'Edit',
        'lesson': lesson,
        'cancel_url': 'lessons:lesson_detail',
        'cancel_id': lesson.pk
    })


@teacher_required
def lesson_delete(request, pk):
    """Delete a lesson."""
    lesson = get_object_or_404(Lesson, pk=pk)

    if request.method == 'POST':
        lesson_title = lesson.title
        lesson.delete()
        messages.success(request, f'Lesson "{lesson_title}" deleted successfully!')
        return redirect('lessons:lesson_list')

    return render(request, 'lessons/confirm_delete.html', {
        'object': lesson,
        'object_type': 'Lesson',
        'cancel_url': 'lessons:lesson_detail',
        'cancel_id': lesson.pk
    })


@teacher_required
@require_http_methods(["POST"])
def lesson_toggle(request, pk):
    """Toggle lesson enabled status (AJAX endpoint)."""
    lesson = get_object_or_404(Lesson, pk=pk)
    lesson.is_enabled = not lesson.is_enabled
    lesson.save()

    return JsonResponse({
        'success': True,
        'is_enabled': lesson.is_enabled,
        'message': f'Lesson {"enabled" if lesson.is_enabled else "disabled"} successfully.'
    })


@teacher_required
@require_http_methods(["POST"])
def reorder_lessons(request):
    """Reorder lessons via drag-and-drop (AJAX endpoint)."""
    try:
        data = json.loads(request.body)
        lesson_ids = data.get('lesson_ids', [])

        with transaction.atomic():
            for index, lesson_id in enumerate(lesson_ids):
                Lesson.objects.filter(pk=lesson_id).update(order=index)

        return JsonResponse({
            'success': True,
            'message': 'Lessons reordered successfully.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# Topic Management Views

@teacher_required
def topic_create(request, lesson_pk):
    """Create a new topic within a lesson."""
    lesson = get_object_or_404(Lesson, pk=lesson_pk)

    if request.method == 'POST':
        form = TopicForm(request.POST)
        if form.is_valid():
            topic = form.save()
            messages.success(request, f'Topic "{topic.title}" created successfully!')
            return redirect('lessons:lesson_detail', lesson_id=lesson.pk)
    else:
        form = TopicForm(initial={'lesson': lesson})

    return render(request, 'lessons/topic_form.html', {
        'form': form,
        'action': 'Create',
        'lesson': lesson,
        'cancel_url': 'lessons:lesson_detail',
        'cancel_id': lesson.pk
    })


@teacher_required
def topic_update(request, pk):
    """Update an existing topic."""
    topic = get_object_or_404(Topic, pk=pk)

    if request.method == 'POST':
        form = TopicForm(request.POST, instance=topic)
        if form.is_valid():
            form.save()
            messages.success(request, f'Topic "{topic.title}" updated successfully!')
            return redirect('lessons:topic_detail', topic_id=topic.pk)
    else:
        form = TopicForm(instance=topic)

    return render(request, 'lessons/topic_form.html', {
        'form': form,
        'action': 'Edit',
        'topic': topic,
        'cancel_url': 'lessons:topic_detail',
        'cancel_id': topic.pk
    })


@teacher_required
def topic_delete(request, pk):
    """Delete a topic."""
    topic = get_object_or_404(Topic, pk=pk)
    lesson = topic.lesson

    if request.method == 'POST':
        topic_title = topic.title
        topic.delete()
        messages.success(request, f'Topic "{topic_title}" deleted successfully!')
        return redirect('lessons:lesson_detail', lesson_id=lesson.pk)

    return render(request, 'lessons/confirm_delete.html', {
        'object': topic,
        'object_type': 'Topic',
        'cancel_url': 'lessons:topic_detail',
        'cancel_id': topic.pk
    })


@teacher_required
@require_http_methods(["POST"])
def topic_toggle(request, pk):
    """Toggle topic enabled status (AJAX endpoint)."""
    topic = get_object_or_404(Topic, pk=pk)
    topic.is_enabled = not topic.is_enabled
    topic.save()

    return JsonResponse({
        'success': True,
        'is_enabled': topic.is_enabled,
        'message': f'Topic {"enabled" if topic.is_enabled else "disabled"} successfully.'
    })


@teacher_required
@require_http_methods(["POST"])
def reorder_topics(request, lesson_pk):
    """Reorder topics within a lesson via drag-and-drop (AJAX endpoint)."""
    lesson = get_object_or_404(Lesson, pk=lesson_pk)

    try:
        data = json.loads(request.body)
        topic_ids = data.get('topic_ids', [])

        with transaction.atomic():
            for index, topic_id in enumerate(topic_ids):
                Topic.objects.filter(pk=topic_id, lesson=lesson).update(order=index)

        return JsonResponse({
            'success': True,
            'message': 'Topics reordered successfully.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# Position Management Views

@teacher_required
def position_create(request, topic_pk):
    """Create a new position within a topic, including move sequences."""
    topic = get_object_or_404(Topic, pk=topic_pk)

    if request.method == 'POST':
        form = PositionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Save position
                position = form.save()

                # Save sequences if provided
                sequence_data = form.cleaned_data.get('sequence_data', [])
                if sequence_data:
                    _save_position_sequences(position, sequence_data)

                messages.success(request, f'Position created successfully with {len(sequence_data)} move(s)!')
            return redirect('lessons:topic_detail', topic_id=topic.pk)
    else:
        form = PositionForm(initial={'topic': topic})

    return render(request, 'lessons/position_form.html', {
        'form': form,
        'action': 'Create',
        'topic': topic,
        'cancel_url': 'lessons:topic_detail',
        'cancel_id': topic.pk
    })


@teacher_required
def position_update(request, pk):
    """Update an existing position and its sequences."""
    position = get_object_or_404(Position, pk=pk)

    if request.method == 'POST':
        form = PositionForm(request.POST, instance=position)
        if form.is_valid():
            with transaction.atomic():
                # Save position
                form.save()

                # Delete existing sequences and recreate from new data
                sequence_data = form.cleaned_data.get('sequence_data', [])
                if sequence_data:
                    position.sequences.all().delete()
                    _save_position_sequences(position, sequence_data)

                messages.success(request, f'Position updated successfully with {len(sequence_data)} move(s)!')
            return redirect('lessons:position_viewer', position_id=position.pk)
    else:
        # Load existing sequences for editing
        existing_sequences = _load_position_sequences(position)
        initial_data = {
            'sequence_data': json.dumps(existing_sequences) if existing_sequences else ''
        }
        form = PositionForm(instance=position, initial=initial_data)

    return render(request, 'lessons/position_form.html', {
        'form': form,
        'action': 'Edit',
        'position': position,
        'cancel_url': 'lessons:position_viewer',
        'cancel_id': position.pk
    })


@teacher_required
def position_delete(request, pk):
    """Delete a position."""
    position = get_object_or_404(Position, pk=pk)
    topic = position.topic

    if request.method == 'POST':
        position.delete()
        messages.success(request, 'Position deleted successfully!')
        return redirect('lessons:topic_detail', topic_id=topic.pk)

    return render(request, 'lessons/confirm_delete.html', {
        'object': position,
        'object_type': 'Position',
        'cancel_url': 'lessons:position_viewer',
        'cancel_id': position.pk
    })


@teacher_required
@require_http_methods(["POST"])
def position_toggle(request, pk):
    """Toggle position enabled status (AJAX endpoint)."""
    position = get_object_or_404(Position, pk=pk)
    position.is_enabled = not position.is_enabled
    position.save()

    return JsonResponse({
        'success': True,
        'is_enabled': position.is_enabled,
        'message': f'Position {"enabled" if position.is_enabled else "disabled"} successfully.'
    })


@teacher_required
@require_http_methods(["POST"])
def reorder_positions(request, topic_pk):
    """Reorder positions within a topic via drag-and-drop (AJAX endpoint)."""
    topic = get_object_or_404(Topic, pk=topic_pk)

    try:
        data = json.loads(request.body)
        position_ids = data.get('position_ids', [])

        with transaction.atomic():
            for index, position_id in enumerate(position_ids):
                Position.objects.filter(pk=position_id, topic=topic).update(order=index)

        return JsonResponse({
            'success': True,
            'message': 'Positions reordered successfully.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# Helper Functions for Position Sequences

def _save_position_sequences(position, sequence_data):
    """
    Save position sequences from JSON data.
    Handles parent-child relationships for variations.
    """
    # Map of temporary IDs from frontend to actual database IDs
    id_map = {}

    # Sort sequences to ensure parents are created before children
    # Main line (parent_move_id=None) first, then variations
    sorted_sequences = sorted(sequence_data, key=lambda x: (
        x.get('parent_move_id') is not None,
        x.get('sequence_order', 0),
        x.get('variation_number', 0)
    ))

    for seq_data in sorted_sequences:
        # Get parent_move from database if it exists
        parent_move_temp_id = seq_data.get('parent_move_id')
        parent_move = None
        if parent_move_temp_id and parent_move_temp_id in id_map:
            parent_move = PositionSequence.objects.get(pk=id_map[parent_move_temp_id])

        # Create the sequence
        sequence = PositionSequence.objects.create(
            position=position,
            sequence_order=seq_data['sequence_order'],
            move_san=seq_data['move_san'],
            explanation=seq_data.get('explanation', ''),
            parent_move=parent_move,
            variation_number=seq_data.get('variation_number', 0)
        )

        # Map temporary ID to actual database ID
        temp_id = seq_data.get('id')
        if temp_id:
            id_map[temp_id] = sequence.pk


def _load_position_sequences(position):
    """
    Load existing sequences and convert to JSON format for the frontend.
    Rebuilds the tree structure from parent-child relationships.
    """
    sequences = position.sequences.all()

    if not sequences:
        return []

    # Convert to list of dicts with frontend format
    sequence_list = []
    for seq in sequences:
        sequence_list.append({
            'id': f'move_{seq.pk}',
            'move_san': seq.move_san,
            'explanation': seq.explanation,
            'parent_move_id': f'move_{seq.parent_move.pk}' if seq.parent_move else None,
            'sequence_order': seq.sequence_order,
            'variation_number': seq.variation_number
        })

    return sequence_list
