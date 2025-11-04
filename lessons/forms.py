"""
Forms for teacher management of lessons, topics, and positions.
"""
import json
from django import forms
from django.core.exceptions import ValidationError
from core.models import Lesson, Topic, Position, PositionSequence


class LessonForm(forms.ModelForm):
    """Form for creating and editing lessons."""

    class Meta:
        model = Lesson
        fields = ['title', 'description', 'difficulty_level', 'is_enabled', 'order']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter lesson title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter lesson description'
            }),
            'difficulty_level': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Display order (0 for first)'
            }),
        }
        help_texts = {
            'is_enabled': 'Uncheck to disable this lesson for students',
            'order': 'Lower numbers appear first in the list',
        }


class TopicForm(forms.ModelForm):
    """Form for creating and editing topics."""

    class Meta:
        model = Topic
        fields = ['lesson', 'title', 'description', 'is_enabled', 'order']
        widgets = {
            'lesson': forms.Select(attrs={
                'class': 'form-control'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter topic title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter topic description'
            }),
            'is_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Display order (0 for first)'
            }),
        }
        help_texts = {
            'is_enabled': 'Uncheck to disable this topic for students',
            'order': 'Lower numbers appear first in the list',
        }


class PositionForm(forms.ModelForm):
    """Form for creating and editing positions with sequence data."""

    # Hidden field for JSON sequence data from JavaScript builder
    sequence_data = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'sequence-data'}),
        help_text='JSON data for move sequences (auto-populated)'
    )

    class Meta:
        model = Position
        fields = ['topic', 'fen', 'description', 'is_sequence_part', 'is_enabled', 'order']
        widgets = {
            'topic': forms.Select(attrs={
                'class': 'form-control'
            }),
            'fen': forms.HiddenInput(attrs={
                'id': 'id_fen'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter position description or explanation'
            }),
            'is_sequence_part': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_is_sequence_part'
            }),
            'is_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Display order (0 for first)'
            }),
        }
        help_texts = {
            'fen': 'Valid FEN notation for the chess position (auto-populated from board)',
            'is_sequence_part': 'Check if this position has move sequences',
            'is_enabled': 'Uncheck to disable this position for students',
            'order': 'Lower numbers appear first in the list',
        }

    def clean_sequence_data(self):
        """Validate sequence data JSON."""
        data = self.cleaned_data.get('sequence_data', '')

        if not data:
            return []

        try:
            sequences = json.loads(data)

            if not isinstance(sequences, list):
                raise ValidationError('Sequence data must be a list')

            # Validate each sequence item
            for seq in sequences:
                required_fields = ['move_san', 'explanation', 'sequence_order', 'variation_number']
                for field in required_fields:
                    if field not in seq:
                        raise ValidationError(f'Missing required field: {field}')

            return sequences
        except json.JSONDecodeError:
            raise ValidationError('Invalid JSON format for sequence data')
        except Exception as e:
            raise ValidationError(f'Error validating sequence data: {str(e)}')

    def clean(self):
        """Additional validation for the form."""
        cleaned_data = super().clean()

        # Auto-check is_sequence_part if sequences exist
        sequence_data = cleaned_data.get('sequence_data', [])
        if sequence_data and len(sequence_data) > 0:
            cleaned_data['is_sequence_part'] = True

        return cleaned_data


class PositionSequenceForm(forms.ModelForm):
    """Form for creating and editing position move sequences."""

    class Meta:
        model = PositionSequence
        fields = ['position', 'sequence_order', 'move_san', 'explanation']
        widgets = {
            'position': forms.Select(attrs={
                'class': 'form-control'
            }),
            'sequence_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Move number in sequence'
            }),
            'move_san': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Move in SAN notation (e.g., Nf3, e4, O-O)'
            }),
            'explanation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Explain why this move is played'
            }),
        }
        help_texts = {
            'move_san': 'Standard Algebraic Notation (e.g., Nf3, e4, O-O)',
            'sequence_order': 'Order of this move in the sequence (1, 2, 3, etc.)',
        }
