"""
Admin configuration for the core app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import (
    Lesson, Topic, Position, PositionSequence,
    Game, GameMove, UserProgress
)
from .chess_engine import ChessEngine


# Custom form with FEN validation
class PositionAdminForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = '__all__'
        widgets = {
            'fen': forms.TextInput(attrs={'size': '80'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_fen(self):
        fen = self.cleaned_data['fen']
        engine = ChessEngine()
        if not engine.is_valid_fen(fen):
            raise forms.ValidationError('Invalid FEN string')
        return fen


# Inline admins
class TopicInline(admin.TabularInline):
    model = Topic
    extra = 1
    fields = ['title', 'description', 'order']
    ordering = ['order']


class PositionInline(admin.TabularInline):
    model = Position
    form = PositionAdminForm
    extra = 1
    fields = ['fen', 'description', 'order', 'is_sequence_part']
    ordering = ['order']


class PositionSequenceInline(admin.TabularInline):
    model = PositionSequence
    extra = 1
    fields = ['sequence_order', 'move_san', 'explanation']
    ordering = ['sequence_order']


class GameMoveInline(admin.TabularInline):
    model = GameMove
    extra = 0
    fields = ['move_number', 'move_san', 'fen_after_move', 'timestamp']
    readonly_fields = ['timestamp']
    ordering = ['move_number']
    can_delete = False


# Main admin classes
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['order', 'title', 'difficulty_level', 'topics_count', 'created_at']
    list_filter = ['difficulty_level', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['order', 'created_at']
    inlines = [TopicInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'order')
        }),
        ('Settings', {
            'fields': ('difficulty_level',)
        }),
    )

    def topics_count(self, obj):
        return obj.get_topics_count()
    topics_count.short_description = 'Topics'


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['title', 'lesson', 'order', 'positions_count', 'created_at']
    list_filter = ['lesson', 'created_at']
    search_fields = ['title', 'description', 'lesson__title']
    ordering = ['lesson__order', 'order']
    inlines = [PositionInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('lesson', 'title', 'description', 'order')
        }),
    )

    def positions_count(self, obj):
        return obj.get_positions_count()
    positions_count.short_description = 'Positions'


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    form = PositionAdminForm
    list_display = ['topic', 'order', 'is_sequence_part', 'fen_preview', 'created_at']
    list_filter = ['topic__lesson', 'topic', 'is_sequence_part', 'created_at']
    search_fields = ['description', 'fen', 'topic__title']
    ordering = ['topic__lesson__order', 'topic__order', 'order']
    inlines = [PositionSequenceInline]

    fieldsets = (
        ('Position Information', {
            'fields': ('topic', 'fen', 'description', 'order')
        }),
        ('Settings', {
            'fields': ('is_sequence_part',)
        }),
    )

    def fen_preview(self, obj):
        return format_html('<code>{}</code>', obj.fen[:50] + '...' if len(obj.fen) > 50 else obj.fen)
    fen_preview.short_description = 'FEN'

    actions = ['validate_fen_strings']

    def validate_fen_strings(self, request, queryset):
        """Validate FEN strings for selected positions."""
        engine = ChessEngine()
        invalid_count = 0

        for position in queryset:
            if not engine.is_valid_fen(position.fen):
                invalid_count += 1
                self.message_user(
                    request,
                    f'Invalid FEN in position {position.id}: {position.fen}',
                    level='ERROR'
                )

        if invalid_count == 0:
            self.message_user(request, 'All selected FEN strings are valid.')
        else:
            self.message_user(
                request,
                f'{invalid_count} invalid FEN string(s) found.',
                level='WARNING'
            )

    validate_fen_strings.short_description = 'Validate FEN strings'


@admin.register(PositionSequence)
class PositionSequenceAdmin(admin.ModelAdmin):
    list_display = ['position', 'sequence_order', 'move_san', 'created_at']
    list_filter = ['position__topic__lesson', 'position__topic', 'created_at']
    search_fields = ['move_san', 'explanation', 'position__description']
    ordering = ['position', 'sequence_order']

    fieldsets = (
        ('Sequence Information', {
            'fields': ('position', 'sequence_order', 'move_san', 'explanation')
        }),
    )


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = [
        'unique_link_short', 'white_player', 'black_player',
        'status', 'current_turn', 'move_count', 'created_at'
    ]
    list_filter = ['status', 'current_turn', 'created_at']
    search_fields = ['unique_link', 'white_player__username', 'black_player__username']
    readonly_fields = ['unique_link', 'created_at', 'updated_at', 'game_link']
    ordering = ['-created_at']
    inlines = [GameMoveInline]

    fieldsets = (
        ('Game Information', {
            'fields': ('unique_link', 'game_link', 'status', 'current_turn')
        }),
        ('Players', {
            'fields': ('white_player', 'black_player')
        }),
        ('Position', {
            'fields': ('position_fen', 'current_fen', 'moves_pgn')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def unique_link_short(self, obj):
        return str(obj.unique_link)[:8] + '...'
    unique_link_short.short_description = 'Game ID'

    def move_count(self, obj):
        return obj.get_move_count()
    move_count.short_description = 'Moves'

    def game_link(self, obj):
        if obj.pk:
            url = f'/game/{obj.unique_link}/'
            return format_html('<a href="{}" target="_blank">{}</a>', url, url)
        return '-'
    game_link.short_description = 'Game Link'


@admin.register(GameMove)
class GameMoveAdmin(admin.ModelAdmin):
    list_display = ['game', 'move_number', 'move_san', 'timestamp']
    list_filter = ['game__status', 'timestamp']
    search_fields = ['game__unique_link', 'move_san']
    readonly_fields = ['timestamp']
    ordering = ['game', 'move_number']


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'completion_percentage', 'last_accessed']
    list_filter = ['lesson', 'last_accessed']
    search_fields = ['user__username', 'lesson__title']
    readonly_fields = ['completion_percentage', 'last_accessed', 'created_at']
    filter_horizontal = ['completed_positions']

    fieldsets = (
        ('Progress Information', {
            'fields': ('user', 'lesson', 'completion_percentage')
        }),
        ('Completed Positions', {
            'fields': ('completed_positions',)
        }),
        ('Timestamps', {
            'fields': ('last_accessed', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def completion_percentage(self, obj):
        return f"{obj.get_completion_percentage()}%"
    completion_percentage.short_description = 'Progress'
