"""
Management command to import lessons from JSON file.

Usage:
    python manage.py import_lessons lessons.json
    python manage.py import_lessons lessons.json --clear
"""
import json
import sys
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Lesson, Topic, Position, PositionSequence


class Command(BaseCommand):
    help = 'Import lessons, topics, positions, and sequences from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Path to JSON file containing lesson data'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing lessons before importing'
        )

    def handle(self, *args, **options):
        json_file = options['json_file']
        clear_existing = options['clear']

        # Read JSON file
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'File "{json_file}" does not exist')
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON in file: {e}')

        # Clear existing data if requested
        if clear_existing:
            self.stdout.write(self.style.WARNING('Clearing existing lessons...'))
            with transaction.atomic():
                PositionSequence.objects.all().delete()
                Position.objects.all().delete()
                Topic.objects.all().delete()
                Lesson.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Cleared all lessons'))

        # Import lessons
        lessons_data = data.get('lessons', [])
        if not lessons_data:
            raise CommandError('No lessons found in JSON file')

        self.stdout.write(f'Importing {len(lessons_data)} lessons...\n')

        with transaction.atomic():
            for lesson_data in lessons_data:
                self.import_lesson(lesson_data)

        self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully imported {len(lessons_data)} lessons!'))

    def import_lesson(self, lesson_data):
        """Import a single lesson with all its topics and positions."""
        lesson_title = lesson_data['title']
        self.stdout.write(f'\n📚 Importing lesson: {lesson_title}')

        # Create lesson
        lesson = Lesson.objects.create(
            title=lesson_data['title'],
            description=lesson_data['description'],
            difficulty_level=lesson_data['difficulty_level'],
            order=lesson_data['order']
        )
        self.stdout.write(f'   ✓ Created lesson: {lesson.title}')

        # Import topics
        topics_data = lesson_data.get('topics', [])
        self.stdout.write(f'   📖 Importing {len(topics_data)} topics...')

        for topic_data in topics_data:
            self.import_topic(lesson, topic_data)

    def import_topic(self, lesson, topic_data):
        """Import a topic with all its positions."""
        topic_title = topic_data['title']
        self.stdout.write(f'      • Topic: {topic_title}')

        # Create topic
        topic = Topic.objects.create(
            lesson=lesson,
            title=topic_data['title'],
            description=topic_data['description'],
            order=topic_data['order']
        )

        # Import positions
        positions_data = topic_data.get('positions', [])
        self.stdout.write(f'        Importing {len(positions_data)} positions...')

        for position_data in positions_data:
            self.import_position(topic, position_data)

    def import_position(self, topic, position_data):
        """Import a position with all its move sequences."""
        position_desc = position_data['description']
        self.stdout.write(f'          ♟ Position: {position_desc}')

        # Create position
        position = Position.objects.create(
            topic=topic,
            description=position_data['description'],
            position_type=position_data['position_type'],
            fen=position_data['fen']
        )

        # Import sequences if this is a sequence position
        sequences_data = position_data.get('sequences', [])
        if sequences_data:
            self.stdout.write(f'            Importing {len(sequences_data)} moves...')
            self.import_sequences(position, sequences_data)

    def import_sequences(self, position, sequences_data):
        """Import move sequences for a position."""
        # Create a mapping from sequence_order to actual PositionSequence objects
        sequence_map = {}

        for seq_data in sequences_data:
            sequence_order = seq_data['sequence_order']
            parent_move_id = seq_data.get('parent_move_id')

            # Determine the actual parent object
            parent_sequence = None
            if parent_move_id is not None:
                parent_sequence = sequence_map.get(parent_move_id)
                if parent_sequence is None:
                    self.stderr.write(
                        self.style.WARNING(
                            f'Warning: Parent move with sequence_order {parent_move_id} not found. '
                            f'Creating orphaned sequence.'
                        )
                    )

            # Create the sequence
            sequence = PositionSequence.objects.create(
                position=position,
                move_san=seq_data['move_san'],
                explanation=seq_data.get('explanation', ''),
                parent_move=parent_sequence,
                sequence_order=sequence_order,
                variation_number=seq_data.get('variation_number', 0)
            )

            # Store in map for future parent references
            sequence_map[sequence_order] = sequence

        self.stdout.write(f'            ✓ Created {len(sequences_data)} move sequences')
