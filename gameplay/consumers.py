"""
WebSocket consumer for real-time chess gameplay.
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import Game, GameMove
from core.chess_engine import ChessEngine

logger = logging.getLogger(__name__)


class GameConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for handling real-time chess games."""

    async def connect(self):
        """Handle WebSocket connection."""
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.room_group_name = f'game_{self.game_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial game state
        game_state = await self.get_game_state()
        await self.send(text_data=json.dumps({
            'type': 'game_state',
            'data': game_state
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'make_move':
                await self.handle_move(data)
            elif message_type == 'join_game':
                await self.handle_join(data)
            elif message_type == 'resign':
                await self.handle_resign(data)
            elif message_type == 'offer_draw':
                await self.handle_draw_offer(data)
            elif message_type == 'accept_draw':
                await self.handle_draw_accept(data)
            elif message_type == 'request_takeback':
                await self.handle_takeback_request(data)
            elif message_type == 'takeback_response':
                await self.handle_takeback_response(data)
            elif message_type == 'request_state':
                game_state = await self.get_game_state()
                await self.send(text_data=json.dumps({
                    'type': 'game_state',
                    'data': game_state
                }))

        except json.JSONDecodeError:
            await self.send_error('Invalid JSON data')
        except Exception as e:
            await self.send_error(str(e))

    async def handle_move(self, data):
        """Handle a move attempt."""
        move_san = data.get('move')
        user_id = self.scope['user'].id

        if not move_san:
            await self.send_error('No move provided')
            return

        # Validate and make move
        result = await self.make_move(user_id, move_san)

        if result['success']:
            # Broadcast move to all players in the room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'move_made',
                    'move': move_san,
                    'game_state': result['game_state']
                }
            )
        else:
            await self.send_error(result['error'])

    async def handle_join(self, data):
        """Handle a player joining the game."""
        user_id = self.scope['user'].id

        # Auto-assign color based on available slot
        result = await self.join_game(user_id)

        if result['success']:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'player_joined',
                    'game_state': result['game_state']
                }
            )
        else:
            await self.send_error(result['error'])

    async def handle_resign(self, data):
        """Handle a player resignation."""
        user_id = self.scope['user'].id
        result = await self.resign_game(user_id)

        if result['success']:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_ended',
                    'reason': 'resignation',
                    'winner': result['winner'],
                    'game_state': result['game_state']
                }
            )

    async def handle_draw_offer(self, data):
        """Handle a draw offer."""
        user_id = self.scope['user'].id
        username = self.scope['user'].username
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'draw_offered',
                'player_id': user_id,
                'username': username
            }
        )

    async def handle_draw_accept(self, data):
        """Handle draw acceptance."""
        result = await self.accept_draw()

        if result['success']:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_ended',
                    'reason': 'draw_accepted',
                    'game_state': result['game_state']
                }
            )

    async def handle_takeback_request(self, data):
        """Handle takeback request."""
        user_id = self.scope['user'].id
        username = self.scope['user'].username

        # Broadcast takeback request to opponent
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'takeback_requested',
                'player_id': user_id,
                'username': username
            }
        )

    async def handle_takeback_response(self, data):
        """Handle takeback response (accept/decline)."""
        accepted = data.get('accepted', False)
        requester_id = data.get('requester_id')

        if accepted:
            # Undo the requester's last move
            result = await self.undo_last_move(requester_id)

            if result['success']:
                # Broadcast updated game state
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'takeback_accepted',
                        'game_state': result['game_state']
                    }
                )
            else:
                await self.send_error(result.get('error', 'Failed to undo move'))
        else:
            # Notify that takeback was declined
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'takeback_declined'
                }
            )

    # Group message handlers
    async def move_made(self, event):
        """Send move to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'move_made',
            'move': event['move'],
            'data': event['game_state']
        }))

    async def player_joined(self, event):
        """Send player joined notification."""
        await self.send(text_data=json.dumps({
            'type': 'player_joined',
            'data': event['game_state']
        }))

    async def game_ended(self, event):
        """Send game ended notification."""
        await self.send(text_data=json.dumps({
            'type': 'game_ended',
            'reason': event['reason'],
            'winner': event.get('winner'),
            'data': event['game_state']
        }))

    async def draw_offered(self, event):
        """Send draw offer notification."""
        await self.send(text_data=json.dumps({
            'type': 'draw_offered',
            'player_id': event['player_id'],
            'username': event['username']
        }))

    async def takeback_requested(self, event):
        """Send takeback request notification."""
        await self.send(text_data=json.dumps({
            'type': 'takeback_requested',
            'player_id': event['player_id'],
            'username': event['username']
        }))

    async def takeback_accepted(self, event):
        """Send takeback accepted notification."""
        await self.send(text_data=json.dumps({
            'type': 'takeback_accepted',
            'data': event['game_state']
        }))

    async def takeback_declined(self, event):
        """Send takeback declined notification."""
        await self.send(text_data=json.dumps({
            'type': 'takeback_declined'
        }))

    async def send_error(self, message):
        """Send error message to client."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))

    # Database operations
    @database_sync_to_async
    def get_game_state(self):
        """Get current game state."""
        try:
            game = Game.objects.select_related('white_player', 'black_player').get(
                unique_link=self.game_id
            )

            moves = GameMove.objects.filter(game=game).order_by('move_number')
            move_history = [
                {'move_number': m.move_number, 'move_san': m.move_san}
                for m in moves
            ]

            return {
                'fen': game.current_fen,
                'status': game.status,
                'current_turn': game.current_turn,
                'white_player': game.white_player.username if game.white_player else None,
                'black_player': game.black_player.username if game.black_player else None,
                'moves_pgn': game.moves_pgn,
                'move_history': move_history,
                'winner': game.winner,
            }
        except Game.DoesNotExist:
            return {'error': 'Game not found'}

    @database_sync_to_async
    def make_move(self, user_id, move_str):
        """Make a move in the game."""
        try:
            # Use select_for_update() to prevent race conditions from concurrent moves
            with transaction.atomic():
                # Don't use select_related() with select_for_update() - causes "FOR UPDATE cannot be applied" error
                game = Game.objects.select_for_update().get(
                    unique_link=self.game_id
                )

                # Check if it's the player's turn
                if game.status != 'in_progress':
                    return {'success': False, 'error': 'Game is not in progress'}

                current_player = User.objects.get(id=user_id)

                if game.current_turn == 'white' and game.white_player != current_player:
                    return {'success': False, 'error': 'Not your turn'}
                if game.current_turn == 'black' and game.black_player != current_player:
                    return {'success': False, 'error': 'Not your turn'}

                # Validate and make move
                engine = ChessEngine(game.current_fen)

                # Try UCI first (from drag-and-drop), then SAN (from click or manual entry)
                import chess
                success = False
                new_fen = None
                error = None
                move_san = None

                # Try UCI format first (e.g., "e2e4")
                try:
                    move_uci = chess.Move.from_uci(move_str)
                    if move_uci in engine.board.legal_moves:
                        try:
                            move_san = engine.board.san(move_uci)
                            engine.board.push(move_uci)
                            new_fen = engine.board.fen()
                            success = True
                            error = None
                            # Log successful SAN conversion for debugging
                            logger.info(f"Move converted: UCI '{move_str}' → SAN '{move_san}'")

                            # Validate that move_san is proper SAN notation, not UCI
                            if move_str.lower() == move_san.lower():
                                logger.warning(
                                    f"WARNING: UCI conversion resulted in same notation! "
                                    f"UCI: '{move_str}' → SAN: '{move_san}' - "
                                    f"This may indicate a conversion issue."
                                )
                        except Exception as e:
                            # This shouldn't happen if move is in legal_moves
                            logger.error(f"Error converting legal move {move_uci} to SAN: {e}")
                            error = f'Move validation error: {str(e)}'
                    else:
                        # Not a legal UCI move, will try SAN next
                        pass
                except (ValueError, chess.InvalidMoveError):
                    # Not valid UCI format, will try SAN next
                    pass

                # If UCI didn't work, try SAN format
                if not success:
                    try:
                        # Create a fresh board for SAN parsing
                        board = chess.Board(game.current_fen)
                        move = board.parse_san(move_str)
                        if move in board.legal_moves:
                            move_san = move_str  # Already in SAN format
                            board.push(move)
                            new_fen = board.fen()
                            success = True
                            logger.info(f"Move accepted as SAN: '{move_san}'")
                        else:
                            error = 'Illegal move - that piece cannot move there'
                    except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError) as e:
                        error = f'Invalid move format: {str(e)}'

                if not success:
                    return {'success': False, 'error': error or 'Invalid move'}

                # Save move with validation
                move_number = game.moves.count() + 1
                game_move = GameMove(
                    game=game,
                    move_number=move_number,
                    move_san=move_san,
                    fen_after_move=new_fen
                )

                # Validate before saving to catch any UCI notation that slipped through
                try:
                    game_move.full_clean()
                    game_move.save()
                    logger.info(f"Move saved: #{move_number} {move_san} → FEN: {new_fen[:50]}...")
                except ValidationError as ve:
                    logger.error(
                        f"Move validation failed! "
                        f"Attempted to save UCI notation as SAN: {move_san}. "
                        f"Validation error: {ve}"
                    )
                    return {
                        'success': False,
                        'error': f'Move notation validation failed: {move_san}'
                    }

                # Update game state
                game.current_fen = new_fen
                game.current_turn = 'black' if game.current_turn == 'white' else 'white'

                # Build PGN from GameMove records instead of engine.get_pgn_moves()
                # This ensures PGN matches actual move history even when engine initialized from FEN
                moves = GameMove.objects.filter(game=game).order_by('move_number')
                pgn_parts = []
                for i, move in enumerate(moves):
                    if i % 2 == 0:  # White's move
                        pgn_parts.append(f"{(i // 2) + 1}. {move.move_san}")
                    else:  # Black's move
                        pgn_parts.append(move.move_san)
                game.moves_pgn = ' '.join(pgn_parts)

                # Check for game over
                if engine.is_checkmate():
                    game.status = 'completed'
                    # The player who just moved won (checkmated the opponent)
                    game.winner = 'white' if previous_turn == 'white' else 'black'
                elif engine.is_stalemate():
                    game.status = 'draw'
                    game.winner = 'draw'

                game.save()
                logger.info(f"Game updated: status={game.status}, turn={game.current_turn}, FEN={game.current_fen[:50]}...")

                # Get updated move history
                move_history = [
                    {'move_number': m.move_number, 'move_san': m.move_san}
                    for m in moves
                ]

                return {
                    'success': True,
                    'game_state': {
                        'fen': game.current_fen,
                        'status': game.status,
                        'current_turn': game.current_turn,
                        'white_player': game.white_player.username if game.white_player else None,
                        'black_player': game.black_player.username if game.black_player else None,
                        'moves_pgn': game.moves_pgn,
                        'move_history': move_history,
                        'is_check': engine.is_check(),
                        'is_checkmate': engine.is_checkmate(),
                        'is_stalemate': engine.is_stalemate(),
                        'winner': game.winner,
                    }
                }

        except Game.DoesNotExist:
            return {'success': False, 'error': 'Game not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @database_sync_to_async
    def join_game(self, user_id):
        """Join a game as a player - auto-assigns to available color."""
        try:
            game = Game.objects.get(unique_link=self.game_id)
            user = User.objects.get(id=user_id)

            if game.status != 'waiting':
                return {'success': False, 'error': 'Game already started'}

            # Auto-assign to available color slot
            if not game.white_player:
                game.white_player = user
                assigned_color = 'white'
            elif not game.black_player:
                game.black_player = user
                assigned_color = 'black'
            else:
                return {'success': False, 'error': 'Game is full - both colors taken'}

            # Start game if both players present
            if game.white_player and game.black_player:
                game.status = 'in_progress'

            game.save()

            return {
                'success': True,
                'assigned_color': assigned_color,
                'game_state': {
                    'fen': game.current_fen,
                    'status': game.status,
                    'current_turn': game.current_turn,
                    'white_player': game.white_player.username if game.white_player else None,
                    'black_player': game.black_player.username if game.black_player else None,
                }
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @database_sync_to_async
    def resign_game(self, user_id):
        """Resign from the game."""
        try:
            game = Game.objects.get(unique_link=self.game_id)
            user = User.objects.get(id=user_id)

            if game.white_player == user:
                winner = 'black'
            elif game.black_player == user:
                winner = 'white'
            else:
                return {'success': False, 'error': 'You are not a player'}

            game.status = 'resigned'
            game.winner = winner
            game.save()

            return {
                'success': True,
                'winner': winner,
                'game_state': {
                    'status': game.status,
                    'winner': winner,
                }
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @database_sync_to_async
    def accept_draw(self):
        """Accept a draw offer."""
        try:
            game = Game.objects.get(unique_link=self.game_id)
            game.status = 'draw'
            game.winner = 'draw'
            game.save()

            return {
                'success': True,
                'game_state': {
                    'status': game.status,
                    'winner': 'draw',
                }
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @database_sync_to_async
    def undo_last_move(self, requester_id):
        """Undo the last move made by the requester."""
        try:
            with transaction.atomic():
                game = Game.objects.select_for_update().get(unique_link=self.game_id)
                requester = User.objects.get(id=requester_id)

                # Determine which color the requester is playing
                if game.white_player == requester:
                    requester_color = 'white'
                elif game.black_player == requester:
                    requester_color = 'black'
                else:
                    return {'success': False, 'error': 'Requester is not a player'}

                # Get all moves for this game
                all_moves = list(GameMove.objects.filter(game=game).order_by('move_number'))

                if not all_moves:
                    return {'success': False, 'error': 'No moves to undo'}

                # Find the last move made by the requester
                # White makes odd-numbered moves (1, 3, 5...), Black makes even-numbered (2, 4, 6...)
                requester_moves = [
                    m for m in all_moves
                    if (requester_color == 'white' and m.move_number % 2 == 1) or
                       (requester_color == 'black' and m.move_number % 2 == 0)
                ]

                if not requester_moves:
                    return {'success': False, 'error': 'No moves to undo'}

                # Get the last move by requester
                last_requester_move = requester_moves[-1]

                # Delete this move
                last_requester_move.delete()

                # Rebuild game state
                remaining_moves = GameMove.objects.filter(game=game).order_by('move_number')

                # Rebuild position from remaining moves
                from core.chess_engine import ChessEngine
                engine = ChessEngine()
                engine.set_position(game.position_fen)

                for move in remaining_moves:
                    engine.make_move_san(move.move_san)

                game.current_fen = engine.get_fen()
                game.current_turn = engine.get_current_turn()

                # Rebuild PGN
                pgn_parts = []
                for i, move in enumerate(remaining_moves):
                    if i % 2 == 0:  # White's move
                        pgn_parts.append(f"{(i // 2) + 1}. {move.move_san}")
                    else:  # Black's move
                        pgn_parts.append(move.move_san)
                game.moves_pgn = ' '.join(pgn_parts)

                game.save()

                # Get updated move history
                move_history = [
                    {'move_number': m.move_number, 'move_san': m.move_san}
                    for m in remaining_moves
                ]

                return {
                    'success': True,
                    'game_state': {
                        'fen': game.current_fen,
                        'status': game.status,
                        'current_turn': game.current_turn,
                        'white_player': game.white_player.username if game.white_player else None,
                        'black_player': game.black_player.username if game.black_player else None,
                        'moves_pgn': game.moves_pgn,
                        'move_history': move_history,
                        'winner': game.winner,
                    }
                }

        except Exception as e:
            logger.error(f"Error undoing move: {str(e)}")
            return {'success': False, 'error': str(e)}
