"""
Chess engine wrapper for move validation and game logic.
"""
import chess
from typing import Dict, List, Optional, Tuple


class ChessEngine:
    """Wrapper around python-chess for move validation and game logic."""

    def __init__(self, fen: Optional[str] = None):
        """Initialize with a FEN position or starting position."""
        self.board = chess.Board(fen) if fen else chess.Board()

    def is_valid_fen(self, fen: str) -> bool:
        """Check if a FEN string is valid."""
        try:
            chess.Board(fen)
            return True
        except ValueError:
            return False

    def get_fen(self) -> str:
        """Get the current position as FEN."""
        return self.board.fen()

    def get_current_turn(self) -> str:
        """Get whose turn it is ('white' or 'black')."""
        return 'white' if self.board.turn == chess.WHITE else 'black'

    def is_valid_move(self, move_san: str) -> bool:
        """Check if a move in SAN notation is legal."""
        try:
            self.board.parse_san(move_san)
            return True
        except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError):
            return False

    def make_move(self, move_san: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Make a move on the board.

        Returns:
            Tuple of (success, new_fen, error_message)
        """
        try:
            move = self.board.parse_san(move_san)
            self.board.push(move)
            return True, self.board.fen(), None
        except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError) as e:
            return False, None, str(e)
        except chess.AmbiguousMoveError as e:
            return False, None, f"Ambiguous move: {e}"

    def get_legal_moves(self) -> List[str]:
        """Get all legal moves in SAN notation."""
        return [self.board.san(move) for move in self.board.legal_moves]

    def is_check(self) -> bool:
        """Check if the current player is in check."""
        return self.board.is_check()

    def is_checkmate(self) -> bool:
        """Check if the current position is checkmate."""
        return self.board.is_checkmate()

    def is_stalemate(self) -> bool:
        """Check if the current position is stalemate."""
        return self.board.is_stalemate()

    def is_game_over(self) -> bool:
        """Check if the game is over."""
        return self.board.is_game_over()

    def get_game_result(self) -> Optional[str]:
        """
        Get the game result if game is over.

        Returns:
            '1-0' (white wins), '0-1' (black wins), '1/2-1/2' (draw), or None
        """
        if not self.is_game_over():
            return None

        if self.is_checkmate():
            return '0-1' if self.board.turn == chess.WHITE else '1-0'
        else:
            return '1/2-1/2'

    def get_pgn_moves(self) -> str:
        """Get all moves in PGN format."""
        moves = []
        board_copy = chess.Board()

        for move_num, move in enumerate(self.board.move_stack, 1):
            if move_num % 2 == 1:
                moves.append(f"{(move_num + 1) // 2}. {board_copy.san(move)}")
            else:
                moves.append(board_copy.san(move))
            board_copy.push(move)

        return ' '.join(moves)

    def reset(self):
        """Reset to starting position."""
        self.board.reset()

    def set_position(self, fen: str) -> Tuple[bool, Optional[str]]:
        """
        Set the board to a specific FEN position.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            self.board = chess.Board(fen)
            return True, None
        except ValueError as e:
            return False, str(e)

    def get_board_dict(self) -> Dict[str, Optional[str]]:
        """
        Get board state as a dictionary for JSON serialization.

        Returns dict with squares as keys (e.g., 'e4') and pieces as values (e.g., 'P', 'n')
        """
        board_dict = {}
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                square_name = chess.square_name(square)
                # Use 'w' prefix for white pieces, 'b' for black
                color_prefix = 'w' if piece.color == chess.WHITE else 'b'
                board_dict[square_name] = f"{color_prefix}{piece.symbol().upper()}"
        return board_dict

    def get_move_history(self) -> List[str]:
        """Get the move history in SAN notation."""
        board_copy = chess.Board()
        moves = []

        for move in self.board.move_stack:
            moves.append(board_copy.san(move))
            board_copy.push(move)

        return moves

    @staticmethod
    def create_fen_from_position(
        pieces: Dict[str, str],
        turn: str = 'white',
        castling: str = 'KQkq',
        en_passant: str = '-',
        halfmove: int = 0,
        fullmove: int = 1
    ) -> str:
        """
        Create a FEN string from piece positions.

        Args:
            pieces: Dict with square names as keys (e.g., 'e4') and piece symbols as values
            turn: 'white' or 'black'
            castling: Castling availability (e.g., 'KQkq', '-')
            en_passant: En passant target square (e.g., 'e3', '-')
            halfmove: Halfmove clock
            fullmove: Fullmove number

        Returns:
            FEN string
        """
        # Create empty board
        board = chess.Board(None)

        # Place pieces
        for square_name, piece_symbol in pieces.items():
            square = chess.parse_square(square_name)
            piece = chess.Piece.from_symbol(piece_symbol)
            board.set_piece_at(square, piece)

        # Set turn
        board.turn = chess.WHITE if turn == 'white' else chess.BLACK

        # Set castling rights
        board.set_castling_fen(castling)

        # Set en passant
        if en_passant != '-':
            board.ep_square = chess.parse_square(en_passant)

        # Set clocks
        board.halfmove_clock = halfmove
        board.fullmove_number = fullmove

        return board.fen()

    @staticmethod
    def get_starting_fen() -> str:
        """Get the FEN for the starting position."""
        return chess.STARTING_FEN

    def undo_move(self) -> bool:
        """
        Undo the last move.

        Returns:
            True if successful, False if no moves to undo
        """
        try:
            self.board.pop()
            return True
        except IndexError:
            return False
