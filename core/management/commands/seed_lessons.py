"""
Management command to seed initial lesson data.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Lesson, Topic, Position, PositionSequence


class Command(BaseCommand):
    help = 'Seeds the database with initial chess lessons and positions'

    def handle(self, *args, **options):
        self.stdout.write('Seeding lessons...')

        with transaction.atomic():
            # Clear existing data
            if self.confirm_action('Do you want to clear existing lessons? (yes/no): '):
                Lesson.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('Cleared existing lessons'))

            # Create lessons
            self.create_lesson_1()
            self.create_lesson_2()
            self.create_lesson_3()

        self.stdout.write(self.style.SUCCESS('Successfully seeded lessons!'))

    def confirm_action(self, message):
        """Ask user for confirmation."""
        response = input(message)
        return response.lower() in ['yes', 'y']

    def create_lesson_1(self):
        """Lesson 1: Basic Checkmates"""
        lesson = Lesson.objects.create(
            order=1,
            title='Basic Checkmates',
            description='Learn fundamental checkmate patterns every chess player must know',
            difficulty_level='beginner'
        )

        # Topic 1: Back Rank Mate
        topic1 = Topic.objects.create(
            lesson=lesson,
            order=1,
            title='Back Rank Mate',
            description='The most common checkmate pattern in chess'
        )

        Position.objects.create(
            topic=topic1,
            order=1,
            fen='6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1',
            description='White to move. The black king is trapped on the back rank by its own pawns.',
            is_sequence_part=False
        )

        Position.objects.create(
            topic=topic1,
            order=2,
            fen='r4rk1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1',
            description='Black has rooks but the king is still vulnerable. Find the winning move.',
            is_sequence_part=False
        )

        # Topic 2: Queen and King Mate
        topic2 = Topic.objects.create(
            lesson=lesson,
            order=2,
            title='Queen and King Checkmate',
            description='How to checkmate with queen and king vs lone king'
        )

        Position.objects.create(
            topic=topic2,
            order=1,
            fen='8/8/8/8/8/4K3/8/4k2Q w - - 0 1',
            description='Final position - deliver checkmate with the queen',
            is_sequence_part=False
        )

        self.stdout.write(f'Created: {lesson.title}')

    def create_lesson_2(self):
        """Lesson 2: Tactical Patterns"""
        lesson = Lesson.objects.create(
            order=2,
            title='Tactical Patterns',
            description='Master essential tactical motifs to win material and games',
            difficulty_level='beginner'
        )

        # Topic 1: Forks
        topic1 = Topic.objects.create(
            lesson=lesson,
            order=1,
            title='Knight Forks',
            description='Using the knight to attack two pieces simultaneously'
        )

        Position.objects.create(
            topic=topic1,
            order=1,
            fen='r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1',
            description='White can fork the king and rook with Nxe5',
            is_sequence_part=False
        )

        # Topic 2: Pins
        topic2 = Topic.objects.create(
            lesson=lesson,
            order=2,
            title='Pins',
            description='Pinning pieces to more valuable pieces or the king'
        )

        Position.objects.create(
            topic=topic2,
            order=1,
            fen='r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQ1RK1 b kq - 0 1',
            description='The knight on f6 is pinned to the king by the bishop on c4',
            is_sequence_part=False
        )

        # Topic 3: Skewers
        topic3 = Topic.objects.create(
            lesson=lesson,
            order=3,
            title='Skewers',
            description='Attack a valuable piece forcing it to move and win material behind it'
        )

        Position.objects.create(
            topic=topic3,
            order=1,
            fen='1k6/8/8/8/8/8/1R6/1K6 w - - 0 1',
            description='White plays Rb8+ skewering the king and back rank',
            is_sequence_part=False
        )

        self.stdout.write(f'Created: {lesson.title}')

    def create_lesson_3(self):
        """Lesson 3: Opening Principles"""
        lesson = Lesson.objects.create(
            order=3,
            title='Opening Principles',
            description='Fundamental principles for the opening phase of the game',
            difficulty_level='beginner'
        )

        # Topic 1: Control the Center
        topic1 = Topic.objects.create(
            lesson=lesson,
            order=1,
            title='Control the Center',
            description='Why and how to control the central squares'
        )

        pos1 = Position.objects.create(
            topic=topic1,
            order=1,
            fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
            description='Starting position. Best first moves control the center.',
            is_sequence_part=True
        )

        PositionSequence.objects.create(
            position=pos1,
            sequence_order=1,
            move_san='e4',
            explanation='Controls the center and opens lines for the bishop and queen'
        )

        PositionSequence.objects.create(
            position=pos1,
            sequence_order=2,
            move_san='e5',
            explanation='Black responds by controlling the center as well'
        )

        PositionSequence.objects.create(
            position=pos1,
            sequence_order=3,
            move_san='Nf3',
            explanation='Develop knight while attacking the e5 pawn'
        )

        # Topic 2: Develop Pieces
        topic2 = Topic.objects.create(
            lesson=lesson,
            order=2,
            title='Develop Your Pieces',
            description='Bring your pieces into the game quickly'
        )

        Position.objects.create(
            topic=topic2,
            order=1,
            fen='rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 1',
            description='Both sides have developed knights. Continue development with bishops.',
            is_sequence_part=False
        )

        # Topic 3: Castle Early
        topic3 = Topic.objects.create(
            lesson=lesson,
            order=3,
            title='Castle Early',
            description='Protect your king and activate your rook'
        )

        Position.objects.create(
            topic=topic3,
            order=1,
            fen='r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 1',
            description='Both sides can castle. White should castle kingside now.',
            is_sequence_part=False
        )

        self.stdout.write(f'Created: {lesson.title}')
