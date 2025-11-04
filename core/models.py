"""
Core models for the chess teaching platform.
"""
import uuid
import re
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import chess


def validate_fen(value):
    """Validate that a string is a valid FEN position."""
    try:
        chess.Board(value)
    except ValueError as e:
        raise ValidationError(f'Invalid FEN string: {e}')


class Lesson(models.Model):
    """A lesson containing multiple topics."""
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    difficulty_level = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default='beginner'
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text='Whether this lesson is visible and accessible to students'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_lessons',
        help_text='Teacher who created this lesson'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Lesson'
        verbose_name_plural = 'Lessons'

    def __str__(self):
        return f"{self.order}. {self.title}"

    def get_topics_count(self):
        return self.topics.count()


class Topic(models.Model):
    """A topic within a lesson."""
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='topics'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_enabled = models.BooleanField(
        default=True,
        help_text='Whether this topic is visible and accessible to students'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Topic'
        verbose_name_plural = 'Topics'

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"

    def get_positions_count(self):
        return self.positions.count()


class Position(models.Model):
    """A chess position within a topic."""
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='positions'
    )
    fen = models.CharField(
        max_length=255,
        validators=[validate_fen],
        help_text='FEN notation of the position'
    )
    description = models.TextField(
        help_text='Explanation of the position or what to learn'
    )
    order = models.PositiveIntegerField(default=0)
    is_sequence_part = models.BooleanField(
        default=False,
        help_text='Is this position part of a move sequence?'
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text='Whether this position is visible and accessible to students'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Position'
        verbose_name_plural = 'Positions'

    def __str__(self):
        return f"{self.topic.title} - Position {self.order}"

    def clean(self):
        """Validate the FEN string."""
        super().clean()
        validate_fen(self.fen)

    def get_board(self):
        """Return a chess.Board object for this position."""
        return chess.Board(self.fen)


class PositionSequence(models.Model):
    """A sequence of moves from a position with branching variation support."""
    position = models.ForeignKey(
        Position,
        on_delete=models.CASCADE,
        related_name='sequences'
    )
    sequence_order = models.PositiveIntegerField(
        help_text='Order of this move in the sequence'
    )
    move_san = models.CharField(
        max_length=10,
        help_text='Move in Standard Algebraic Notation (e.g., Nf3, e4)'
    )
    explanation = models.TextField(
        help_text='Explanation of why this move is played'
    )
    parent_move = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='variations',
        null=True,
        blank=True,
        help_text='Parent move for variation branches. Null for main line.'
    )
    variation_number = models.PositiveIntegerField(
        default=0,
        help_text='Variation number at this level (0 for main line)'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sequence_order', 'variation_number']
        verbose_name = 'Position Sequence'
        verbose_name_plural = 'Position Sequences'
        unique_together = [['position', 'parent_move', 'sequence_order', 'variation_number']]

    def __str__(self):
        return f"{self.position} - Move {self.sequence_order}: {self.move_san}"

    def clean(self):
        """Validate that the move is legal in the position, considering branching."""
        super().clean()
        try:
            board = self.position.get_board()

            # Build the move chain from root to this move
            move_chain = self._get_move_chain()

            # Apply all moves in the chain
            for move in move_chain:
                board.push_san(move.move_san)

            # Try to apply this move
            board.push_san(self.move_san)
        except (ValueError, chess.InvalidMoveError) as e:
            raise ValidationError(f'Invalid move: {e}')

    def _get_move_chain(self):
        """Get ordered list of moves from root to parent of this move."""
        chain = []
        current = self.parent_move

        # Build chain backwards from parent to root
        while current is not None:
            chain.insert(0, current)
            current = current.parent_move

        return chain

    def get_variations_at_move(self):
        """Get all variation moves that branch from this move."""
        return self.variations.all()

    def is_main_line(self):
        """Check if this move is part of the main line (no parent)."""
        return self.parent_move is None and self.variation_number == 0


class Game(models.Model):
    """A live chess game."""
    STATUS_CHOICES = [
        ('waiting', 'Waiting for Players'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('draw', 'Draw'),
        ('resigned', 'Resigned'),
    ]

    TURN_CHOICES = [
        ('white', 'White'),
        ('black', 'Black'),
    ]

    WINNER_CHOICES = [
        ('white', 'White'),
        ('black', 'Black'),
        ('draw', 'Draw'),
    ]

    unique_link = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
    position_fen = models.CharField(
        max_length=255,
        validators=[validate_fen],
        help_text='Starting position FEN'
    )
    current_fen = models.CharField(
        max_length=255,
        validators=[validate_fen],
        help_text='Current position FEN'
    )
    white_player = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='games_as_white'
    )
    black_player = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='games_as_black'
    )
    moves_pgn = models.TextField(
        blank=True,
        default='',
        help_text='Game moves in PGN format'
    )
    current_turn = models.CharField(
        max_length=5,
        choices=TURN_CHOICES,
        default='white'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='waiting'
    )
    winner = models.CharField(
        max_length=5,
        choices=WINNER_CHOICES,
        null=True,
        blank=True,
        help_text='Winner of the game (white, black, or draw)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Game'
        verbose_name_plural = 'Games'

    def __str__(self):
        white = self.white_player.username if self.white_player else 'Waiting'
        black = self.black_player.username if self.black_player else 'Waiting'
        return f"Game {self.unique_link} - {white} vs {black}"

    def clean(self):
        """Validate FEN strings."""
        super().clean()
        validate_fen(self.position_fen)
        validate_fen(self.current_fen)

    def get_board(self):
        """Return a chess.Board object for the current position."""
        return chess.Board(self.current_fen)

    def get_move_count(self):
        """Return the number of moves played."""
        return self.moves.count()


class GameMove(models.Model):
    """A single move in a game."""
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name='moves'
    )
    move_number = models.PositiveIntegerField()
    move_san = models.CharField(
        max_length=10,
        help_text='Move in Standard Algebraic Notation'
    )
    fen_after_move = models.CharField(
        max_length=255,
        validators=[validate_fen],
        help_text='Board position after this move'
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['move_number']
        verbose_name = 'Game Move'
        verbose_name_plural = 'Game Moves'
        unique_together = [['game', 'move_number']]

    def clean(self):
        """Validate that move_san contains SAN notation, not UCI."""
        super().clean()

        if self.move_san:
            # Pattern to detect UCI notation (e.g., e2e4, g1f3, e7e8q)
            uci_pattern = re.compile(r'^[a-h][1-8][a-h][1-8][qrbn]?$')

            if uci_pattern.match(self.move_san.lower()):
                raise ValidationError({
                    'move_san': f'Invalid notation format. Expected SAN notation (e.g., "e4", "Nf3", "O-O"), '
                                f'but received UCI notation: "{self.move_san}". '
                                f'Please convert to Standard Algebraic Notation.'
                })

            # Additional check: SAN should contain piece notation or be lowercase pawn moves
            # Valid patterns: Kf3, Nxe5, e4, exd5, O-O, O-O-O, etc.
            # Pawn captures like exd5, gxf4 are valid SAN (pattern: [a-h]x[a-h][1-8])
            # Should NOT be all lowercase 4+ characters UNLESS it's a pawn capture
            if len(self.move_san) >= 4 and self.move_san.islower():
                # Check if it's a valid pawn capture (e.g., exd5, gxf4, axb3)
                pawn_capture_pattern = re.compile(r'^[a-h]x[a-h][1-8][=]?[QRBN]?$')
                if not pawn_capture_pattern.match(self.move_san):
                    raise ValidationError({
                        'move_san': f'Move notation "{self.move_san}" appears to be in UCI format. '
                                    f'Please use Standard Algebraic Notation (e.g., "Nf3", "e4", "O-O").'
                    })

    def __str__(self):
        return f"{self.game.unique_link} - Move {self.move_number}: {self.move_san}"


class UserProgress(models.Model):
    """Track user progress through lessons."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lesson_progress'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='user_progress'
    )
    completed_positions = models.ManyToManyField(
        Position,
        blank=True,
        related_name='completed_by_users'
    )
    last_accessed = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'User Progress'
        verbose_name_plural = 'User Progress'
        unique_together = [['user', 'lesson']]

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title}"

    def get_completion_percentage(self):
        """Calculate completion percentage for this lesson."""
        total_positions = Position.objects.filter(
            topic__lesson=self.lesson
        ).count()
        if total_positions == 0:
            return 0
        completed = self.completed_positions.count()
        return int((completed / total_positions) * 100)
