// Live Chess Game JavaScript with WebSocket
(function() {
    'use strict';

    let board = null;
    let game = null;
    let chess = null; // Chess.js instance for move validation
    let annotations = null; // Board annotations instance
    let socket = null;
    let userColor = null; // Will be set when game state loads
    let boardFlipped = false; // Track if board has been flipped
    let currentFen = null; // Track current FEN since Chessboard.js has no .fen() method
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;

    // Initialize chessboard
    const config = {
        draggable: true,
        position: STARTING_FEN,
        pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
        onDragStart: onDragStart,
        onDrop: onDrop,
        onSnapEnd: onSnapEnd
    };

    board = Chessboard('board', config);
    currentFen = STARTING_FEN; // Initialize FEN tracker

    // Initialize Chess.js for move validation and legal moves
    chess = new Chess(STARTING_FEN);

    // Define move callback for click-to-move functionality
    function handleClickMove(fromSquare, toSquare) {
        console.log('Click-to-move:', fromSquare, '→', toSquare);

        // Validate it's user's turn and game is in progress
        const gameStatus = $('#gameStatus').text().trim();
        if (gameStatus !== 'In Progress') {  // Title case to match updateGameState
            console.log('Game not in progress:', gameStatus);
            showToast('Game is not in progress', 'warning');
            return;
        }

        const currentTurnText = $('#currentTurn').text().trim();
        const currentTurn = currentTurnText === 'White' ? 'white' : 'black';

        if (userColor !== currentTurn) {
            console.log('Not your turn');
            showToast('Not your turn!', 'warning');
            return;
        }

        // Construct move in UCI notation
        const move = fromSquare + toSquare;
        console.log('Sending move to server:', move);

        // Send move to server
        socket.send(JSON.stringify({
            type: 'make_move',
            move: move
        }));

        // Clear selection after initiating move
        if (annotations) {
            annotations.clearSelection();
        }
    }

    // Initialize board annotations (wait for DOM to be fully ready)
    setTimeout(function() {
        console.log('Initializing BoardAnnotations with Chess instance:', chess);
        annotations = new BoardAnnotations('board', chess, handleClickMove);
        console.log('BoardAnnotations initialized:', annotations);
    }, 500);

    // Connect to WebSocket
    connectWebSocket();

    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/game/${GAME_ID}/`;

        socket = new WebSocket(wsUrl);

        socket.onopen = function(e) {
            console.log('WebSocket connected');
            reconnectAttempts = 0;
            showStatus('Connected', 'success');

            // Request current game state
            socket.send(JSON.stringify({
                type: 'request_state'
            }));
        };

        socket.onmessage = function(event) {
            const data = JSON.parse(event.data);
            console.log('WebSocket message received:', data);
            handleWebSocketMessage(data);
        };

        socket.onerror = function(error) {
            console.error('WebSocket error:', error);
            showStatus('Connection error', 'error');
        };

        socket.onclose = function(event) {
            console.log('WebSocket closed');
            showStatus('Disconnected', 'warning');

            // Attempt to reconnect
            if (reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                setTimeout(function() {
                    console.log(`Reconnecting... Attempt ${reconnectAttempts}`);
                    connectWebSocket();
                }, 2000 * reconnectAttempts);
            }
        };
    }

    function handleWebSocketMessage(data) {
        console.log('Handling message type:', data.type);
        switch (data.type) {
            case 'game_state':
                updateGameState(data.data);
                break;
            case 'move_made':
                handleMoveMade(data);
                break;
            case 'player_joined':
                console.log('Player joined, updating state');
                updateGameState(data.data);
                showToast('Player joined!', 'success');
                hideJoinButtons();
                break;
            case 'game_ended':
                handleGameEnded(data);
                break;
            case 'draw_offered':
                handleDrawOffer(data);
                break;
            case 'takeback_requested':
                handleTakebackRequest(data);
                break;
            case 'takeback_accepted':
                handleTakebackAccepted(data);
                break;
            case 'takeback_declined':
                handleTakebackDeclined();
                break;
            case 'error':
                console.error('WebSocket error:', data.message);
                showToast(data.message, 'error');
                break;
        }
    }

    function updateGameState(state) {
        console.log('Updating game state:', state);

        if (state.error) {
            showToast(state.error, 'error');
            return;
        }

        // Determine user's color based on game state
        if (!userColor) {
            console.log('Detecting user color - Current username:', CURRENT_USERNAME);
            console.log('White player:', state.white_player, 'Black player:', state.black_player);

            if (state.white_player === CURRENT_USERNAME) {
                userColor = 'white';
                console.log('User is WHITE');
            } else if (state.black_player === CURRENT_USERNAME) {
                userColor = 'black';
                console.log('User is BLACK');
            }
        }

        // Flip board for black player (only once)
        if (userColor === 'black' && !boardFlipped) {
            console.log('Flipping board for black player');
            board.flip();
            boardFlipped = true;
        }

        // Update board position
        console.log('Setting board position to FEN from server:', state.fen);
        const oldFen = currentFen;
        board.position(state.fen);
        currentFen = state.fen; // Update FEN tracker
        console.log('Board updated. Old FEN:', oldFen, '→ New FEN:', currentFen);

        // Update Chess.js instance with new position
        if (chess) {
            chess.load(state.fen);
        }

        // Clear selection and legal move dots when position updates
        if (annotations) {
            annotations.clearSelection();
        }

        // Update game info
        $('#whitePlayer').text(state.white_player || 'Waiting...');
        $('#blackPlayer').text(state.black_player || 'Waiting...');
        // Convert status to title case (e.g., "in_progress" → "In Progress")
        const statusText = state.status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        $('#gameStatus').text(statusText);
        $('#currentTurn').text(state.current_turn === 'white' ? 'White' : 'Black');

        // Show whose turn it is
        if (userColor && state.status === 'in_progress') {
            if (state.current_turn === userColor) {
                showStatus('Your turn!', 'success');
            } else {
                showStatus('Opponent\'s turn', 'info');
            }
        }

        // Update move history
        if (state.move_history) {
            updateMoveHistory(state.move_history);
        }

        // Check for check/checkmate
        if (state.is_checkmate) {
            showToast('Checkmate!', 'success');
        } else if (state.is_check) {
            showToast('Check!', 'warning');
        } else if (state.is_stalemate) {
            showToast('Stalemate!', 'info');
        }

        // Update button states
        updateButtonStates(state);

        // Hide join buttons if game started
        if (state.status === 'in_progress' || state.status === 'completed') {
            hideJoinButtons();
        }
    }

    function hideJoinButtons() {
        $('#joinGameSection').fadeOut(300);
    }

    function handleMoveMade(data) {
        updateGameState(data.data);
        playMoveSound();

        // Show takeback button after user makes a move
        // Check if the move was made by the current user
        const moveHistory = data.data.move_history;
        if (moveHistory && moveHistory.length > 0) {
            const lastMove = moveHistory[moveHistory.length - 1];
            const lastMoveNumber = lastMove.move_number;

            // Determine if this was the current user's move
            // White: odd move numbers (1, 3, 5...), Black: even move numbers (2, 4, 6...)
            const wasWhiteMove = lastMoveNumber % 2 === 1;
            const wasCurrentUserMove = (wasWhiteMove && userColor === 'white') || (!wasWhiteMove && userColor === 'black');

            if (wasCurrentUserMove) {
                $('#takebackBtn').show();
            }
        }
    }

    function handleGameEnded(data) {
        updateGameState(data.data);

        // Disable game action buttons
        $('#resignBtn, #drawBtn').prop('disabled', true);

        // Show game result modal
        showGameResultModal(data);
    }

    function showGameResultModal(data) {
        const modal = $('#gameResultModal');
        const icon = $('#resultIcon');
        const title = $('#resultTitle');
        const message = $('#resultMessage');

        // Determine icon, title, and message based on result
        let iconText = '';
        let titleText = '';
        let messageText = '';

        const winner = data.winner;
        const reason = data.reason;

        if (reason === 'resignation') {
            iconText = winner === 'white' ? '♔' : '♚';
            titleText = `${winner.charAt(0).toUpperCase() + winner.slice(1)} Wins!`;
            messageText = `${winner === 'white' ? 'Black' : 'White'} resigned`;
        } else if (reason === 'draw_accepted') {
            iconText = '🤝';
            titleText = 'Game Drawn';
            messageText = 'Draw accepted by mutual agreement';
        } else if (data.data && data.data.is_checkmate) {
            iconText = winner === 'white' ? '♔' : '♚';
            titleText = `${winner.charAt(0).toUpperCase() + winner.slice(1)} Wins!`;
            messageText = 'Checkmate!';
        } else if (data.data && data.data.is_stalemate) {
            iconText = '🤝';
            titleText = 'Game Drawn';
            messageText = 'Stalemate';
        } else {
            iconText = '🏁';
            titleText = 'Game Over';
            messageText = winner === 'draw' ? 'Draw' : `${winner.charAt(0).toUpperCase() + winner.slice(1)} wins`;
        }

        // Update modal content
        icon.text(iconText);
        title.text(titleText);
        message.text(messageText);

        // Show modal with animation
        modal.css('display', 'flex').hide().fadeIn(300);
    }

    // Close modal handlers
    $('#closeResultModal, #closeResultBtn').on('click', function() {
        $('#gameResultModal').fadeOut(300);
    });

    // Close on background click
    $('#gameResultModal').on('click', function(e) {
        if (e.target === this) {
            $(this).fadeOut(300);
        }
    });

    function handleDrawOffer(data) {
        // Check if current user is the one who offered the draw
        if (data.username === CURRENT_USERNAME) {
            // Don't show dialog to the player who offered
            showToast('Draw offer sent to opponent', 'info');
            return;
        }

        // Show dialog only to opponent
        if (confirm('Your opponent offers a draw. Accept?')) {
            socket.send(JSON.stringify({
                type: 'accept_draw'
            }));
        }
    }

    function handleTakebackRequest(data) {
        // Check if current user is the one who requested
        if (data.username === CURRENT_USERNAME) {
            showToast('Take back request sent to opponent', 'info');
            return;
        }

        // Show dialog to opponent
        if (confirm(`${data.username} requests to take back their last move. Accept?`)) {
            socket.send(JSON.stringify({
                type: 'takeback_response',
                accepted: true,
                requester_id: data.player_id
            }));
        } else {
            socket.send(JSON.stringify({
                type: 'takeback_response',
                accepted: false,
                requester_id: data.player_id
            }));
        }
    }

    function handleTakebackAccepted(data) {
        // Update game state with undone move
        updateGameState(data.data);
        showToast('Take back accepted - move undone', 'success');

        // Hide takeback button
        $('#takebackBtn').hide();
    }

    function handleTakebackDeclined() {
        showToast('Take back request declined', 'warning');
    }

    function onDragStart(source, piece, position, orientation) {
        console.log('=== DRAG START ===');
        console.log('Source square:', source, 'Piece:', piece);
        console.log('User color:', userColor);
        console.log('Current board FEN:', currentFen);
        console.log('Board orientation:', board.orientation());

        // Keep legal move indicators visible during drag
        // They will be cleared after move completion or position update

        // Don't allow moves if user color not set
        if (!userColor) {
            console.log('User color not set');
            return false;
        }

        // Don't allow moves if game not in progress
        const gameStatus = $('#gameStatus').text().trim();
        if (gameStatus !== 'In Progress') {  // Title case to match updateGameState
            console.log('Game not in progress:', gameStatus);
            return false;
        }

        // Don't allow moves if not your turn
        const currentTurnText = $('#currentTurn').text().trim();
        const currentTurn = currentTurnText === 'White' ? 'white' : 'black';

        if (userColor !== currentTurn) {
            console.log('Not your turn - userColor:', userColor, 'currentTurn:', currentTurn);
            showToast('Not your turn!', 'warning');
            return false;
        }

        // Only allow dragging your own pieces
        if ((userColor === 'white' && piece.search(/^w/) === -1) ||
            (userColor === 'black' && piece.search(/^b/) === -1)) {
            console.log('Not your piece');
            showToast('You can only move your own pieces!', 'warning');
            return false;
        }

        return true;
    }

    function onDrop(source, target) {
        console.log('=== DROP ===');
        console.log('Move:', source, '→', target);

        // If dropped on same square, just cancel (this happens with quick clicks)
        if (source === target) {
            console.log('Dropped on same square - canceling');
            return 'snapback';
        }

        // Construct move in UCI notation
        const move = source + target;
        console.log('Sending UCI move to server:', move);

        // Send move to server
        socket.send(JSON.stringify({
            type: 'make_move',
            move: move
        }));

        // Return 'snapback' to revert, server will update if valid
        return 'snapback';
    }

    function onSnapEnd() {
        // board.position(game.fen());
    }

    function updateMoveHistory(moves) {
        const historyDiv = $('#moveHistory');
        historyDiv.empty();

        moves.forEach(function(move, index) {
            if (index % 2 === 0) {
                historyDiv.append(`<div class="move-pair"><span class="move-number">${Math.floor(index / 2) + 1}.</span> `);
            }
            historyDiv.append(`<span class="move">${move.move_san}</span> `);
            if (index % 2 === 1 || index === moves.length - 1) {
                historyDiv.append('</div>');
            }
        });

        // Scroll to bottom
        historyDiv.scrollTop(historyDiv[0].scrollHeight);
    }

    function updateButtonStates(state) {
        const isInProgress = state.status === 'in_progress';
        $('#resignBtn, #drawBtn').prop('disabled', !isInProgress);
    }

    // Button handlers
    $('#resignBtn').on('click', function() {
        if (confirm('Are you sure you want to resign?')) {
            socket.send(JSON.stringify({
                type: 'resign'
            }));
        }
    });

    $('#drawBtn').on('click', function() {
        socket.send(JSON.stringify({
            type: 'offer_draw'
        }));
        showToast('Draw offer sent', 'info');
    });

    $('#takebackBtn').on('click', function() {
        socket.send(JSON.stringify({
            type: 'request_takeback'
        }));
        showToast('Take back request sent', 'info');
    });

    $('#copyLinkBtn').on('click', function() {
        const link = window.location.href;
        navigator.clipboard.writeText(link).then(function() {
            showToast('Link copied to clipboard!', 'success');
        });
    });

    // Join game button
    $('#joinGameBtn').on('click', function() {
        console.log('Attempting to join game...');

        $(this).prop('disabled', true).text('Joining...');

        socket.send(JSON.stringify({
            type: 'join_game'
            // Color will be auto-assigned by backend
        }));

        // Re-enable after 2 seconds in case of failure
        const btn = $(this);
        setTimeout(function() {
            btn.prop('disabled', false).text('Join Game');
        }, 2000);
    });

    // Utility functions
    function playMoveSound() {
        // You can add a move sound here
    }

    function showStatus(message, type) {
        const statusDiv = $('#connectionStatus');
        statusDiv.text(message);
        statusDiv.removeClass('text-green-600 text-red-600 text-yellow-600');

        if (type === 'success') {
            statusDiv.addClass('text-green-600');
        } else if (type === 'error') {
            statusDiv.addClass('text-red-600');
        } else {
            statusDiv.addClass('text-yellow-600');
        }
    }

    function showToast(message, type = 'info') {
        const toast = $('#toast');
        toast.text(message);
        toast.removeClass('hidden bg-blue-500 bg-green-500 bg-red-500 bg-yellow-500');

        if (type === 'success') {
            toast.addClass('bg-green-500');
        } else if (type === 'error') {
            toast.addClass('bg-red-500');
        } else if (type === 'warning') {
            toast.addClass('bg-yellow-500');
        } else {
            toast.addClass('bg-blue-500');
        }

        toast.fadeIn();
        setTimeout(function() {
            toast.fadeOut();
        }, 3000);
    }
})();
