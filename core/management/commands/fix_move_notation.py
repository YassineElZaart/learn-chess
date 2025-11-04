"""
Django management command to fix UCI notation in GameMove records.
Converts UCI moves (e2e4) to SAN notation (e4, Nf3, etc.)
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Game, GameMove
import chess
import re


class Command(BaseCommand):
    help = 'Fix UCI notation in GameMove records by converting to SAN notation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without actually changing the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        self.stdout.write('Scanning GameMove records for UCI notation...\n')

        # Pattern to detect UCI notation (e.g., e2e4, g1f3, e7e8q)
        uci_pattern = re.compile(r'^[a-h][1-8][a-h][1-8][qrbn]?$')

        total_moves = 0
        corrupted_moves = 0
        fixed_moves = 0
        failed_moves = 0

        # Process each game separately to maintain position context
        games = Game.objects.all().order_by('created_at')

        for game in games:
            moves = GameMove.objects.filter(game=game).order_by('move_number')

            if not moves.exists():
                continue

            total_moves += moves.count()

            # Initialize chess board with game's starting position
            try:
                board = chess.Board(game.position_fen)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to initialize board for game {game.unique_link}: {e}'
                    )
                )
                failed_moves += moves.count()
                continue

            # Process moves in order
            for move_obj in moves:
                move_san = move_obj.move_san

                # Check if this looks like UCI notation
                if uci_pattern.match(move_san.lower()):
                    corrupted_moves += 1

                    if dry_run:
                        self.stdout.write(
                            f'  [DRY RUN] Would fix: Game {game.unique_link}, '
                            f'Move {move_obj.move_number}: "{move_san}" '
                        )
                    else:
                        # Try to convert UCI to SAN
                        try:
                            # Parse UCI move
                            uci_move = chess.Move.from_uci(move_san.lower())

                            # Check if move is legal in current position
                            if uci_move in board.legal_moves:
                                # Convert to SAN
                                san = board.san(uci_move)

                                # Update the move
                                move_obj.move_san = san
                                move_obj.save()

                                # Push move to maintain board state
                                board.push(uci_move)

                                fixed_moves += 1
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'  Fixed: Game {game.unique_link}, '
                                        f'Move {move_obj.move_number}: "{move_san}" → "{san}"'
                                    )
                                )
                            else:
                                failed_moves += 1
                                self.stdout.write(
                                    self.style.ERROR(
                                        f'  Illegal move: Game {game.unique_link}, '
                                        f'Move {move_obj.move_number}: "{move_san}"'
                                    )
                                )
                        except Exception as e:
                            failed_moves += 1
                            self.stdout.write(
                                self.style.ERROR(
                                    f'  Failed to convert: Game {game.unique_link}, '
                                    f'Move {move_obj.move_number}: "{move_san}" - {e}'
                                )
                            )
                else:
                    # Move looks like SAN already, just push it to maintain board state
                    try:
                        # Try to parse as SAN
                        move = board.parse_san(move_san)
                        board.push(move)
                    except Exception as e:
                        # If we can't parse it, try to continue anyway
                        self.stdout.write(
                            self.style.WARNING(
                                f'  Warning: Could not parse SAN move: Game {game.unique_link}, '
                                f'Move {move_obj.move_number}: "{move_san}" - {e}'
                            )
                        )

        # Print summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write('='*60)
        self.stdout.write(f'Total moves scanned: {total_moves}')
        self.stdout.write(f'Corrupted moves found (UCI notation): {corrupted_moves}')

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'Moves that would be fixed: {corrupted_moves - failed_moves}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Moves successfully fixed: {fixed_moves}'
                )
            )

        if failed_moves > 0:
            self.stdout.write(
                self.style.ERROR(
                    f'Moves that could not be fixed: {failed_moves}'
                )
            )

        self.stdout.write('='*60)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '\nThis was a DRY RUN. Run without --dry-run to apply changes.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    '\nDatabase has been updated!'
                )
            )
