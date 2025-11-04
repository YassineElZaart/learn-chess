// Board Editor JavaScript
(function() {
    'use strict';

    let board = null;
    let currentTurn = 'white';
    let selectedPiece = null;
    let trashMode = false;
    let selectedColor = null;

    // Check if we should skip board initialization (when position_sequence_builder.js is in control)
    if (window.SKIP_BOARD_INIT) {
        // Export utilities for position_sequence_builder to use
        window.BoardEditorUtils = {
            getSelectedPiece: () => selectedPiece,
            setSelectedPiece: (piece) => { selectedPiece = piece; },
            getTrashMode: () => trashMode,
            setTrashMode: (mode) => { trashMode = mode; },
            getCurrentTurn: () => currentTurn,
            setCurrentTurn: (turn) => { currentTurn = turn; }
        };
        return;
    }

    // Initialize board with piece images from Wikipedia
    const config = {
        draggable: true,
        dropOffBoard: 'trash',
        sparePieces: false,
        position: STARTING_FEN || 'start',
        pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
        onDragStart: onDragStart,
        onDrop: onDrop,
        onSnapEnd: onSnapEnd
    };

    board = Chessboard('board', config);

    // Initial FEN update
    setTimeout(() => updateFEN(), 100);

    function onDragStart(source, piece, position, orientation) {
        // Allow dragging in editor mode
        return true;
    }

    function onDrop(source, target) {
        // Allow any drop in editor mode
        return;
    }

    function onSnapEnd() {
        updateFEN();
    }

    function updateFEN() {
        const position = board.position();
        const fen = createFEN(position, currentTurn);
        $('#fenDisplay').text(fen);
    }

    function createFEN(position, turn) {
        // Convert board position to FEN
        let fen = '';
        const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];

        for (let rank = 8; rank >= 1; rank--) {
            let emptyCount = 0;
            for (let file of files) {
                const square = file + rank;
                const piece = position[square];

                if (piece) {
                    if (emptyCount > 0) {
                        fen += emptyCount;
                        emptyCount = 0;
                    }
                    // Convert piece notation (wP -> P, bP -> p)
                    const pieceChar = piece.charAt(1);
                    fen += piece.charAt(0) === 'w' ? pieceChar : pieceChar.toLowerCase();
                } else {
                    emptyCount++;
                }
            }
            if (emptyCount > 0) {
                fen += emptyCount;
            }
            if (rank > 1) {
                fen += '/';
            }
        }

        // Add turn, castling, en passant, halfmove, fullmove
        fen += ` ${turn === 'white' ? 'w' : 'b'} KQkq - 0 1`;
        return fen;
    }

    // Button handlers
    $('#startBtn').on('click', function() {
        board.start();
        currentTurn = 'white';
        updateFEN();
        updateTurnButtons();
    });

    $('#clearBtn').on('click', function() {
        board.clear();
        updateFEN();
    });

    $('#flipBtn').on('click', function() {
        board.flip();
    });

    $('#whiteTurnBtn').on('click', function() {
        currentTurn = 'white';
        updateFEN();
        updateTurnButtons();
    });

    $('#blackTurnBtn').on('click', function() {
        currentTurn = 'black';
        updateFEN();
        updateTurnButtons();
    });

    function updateTurnButtons() {
        if (currentTurn === 'white') {
            $('#whiteTurnBtn').removeClass('btn-secondary').addClass('btn-primary');
            $('#blackTurnBtn').removeClass('btn-primary').addClass('btn-secondary');
            // Update turn display
            $('#currentTurnDisplay').html('<span style="font-size: 1.5rem;">♔</span> White');
        } else {
            $('#blackTurnBtn').removeClass('btn-secondary').addClass('btn-primary');
            $('#whiteTurnBtn').removeClass('btn-primary').addClass('btn-secondary');
            // Update turn display
            $('#currentTurnDisplay').html('<span style="font-size: 1.5rem;">♚</span> Black');
        }
    }

    // Color selection handler for game creation
    $('.color-choice-editor').on('click', function() {
        const color = $(this).data('color');
        selectedColor = color;

        // Update UI
        $('.color-choice-editor').removeClass('selected');
        $(this).addClass('selected');

        // Enable generate link button
        const generateBtn = $('#generateLinkBtn');
        generateBtn.prop('disabled', false);
        generateBtn.css({
            'opacity': '1',
            'cursor': 'pointer'
        });

        showToast(`Selected: Play as ${color.charAt(0).toUpperCase() + color.slice(1)}`, 'success');
    });

    // Piece selection
    $('.piece-btn').on('click', function() {
        selectedPiece = $(this).data('piece');
        trashMode = false;
        $('.piece-btn').removeClass('active');
        $('.eraser-btn').removeClass('active');
        $(this).addClass('active');

        const pieceNames = {
            'wK': '♔ White King', 'wQ': '♕ White Queen', 'wR': '♖ White Rook',
            'wB': '♗ White Bishop', 'wN': '♘ White Knight', 'wP': '♙ White Pawn',
            'bK': '♚ Black King', 'bQ': '♛ Black Queen', 'bR': '♜ Black Rook',
            'bB': '♝ Black Bishop', 'bN': '♞ Black Knight', 'bP': '♟ Black Pawn'
        };

        showToast('Selected: ' + (pieceNames[selectedPiece] || selectedPiece), 'success');
    });

    $('#trashBtn').on('click', function() {
        trashMode = true;
        selectedPiece = null;
        $('.piece-btn').removeClass('active');
        $('.eraser-btn').removeClass('active');
        $(this).addClass('active');
        showToast('🧹 Eraser mode - Click pieces to remove', 'info');
    });

    // Board click handler for piece placement and eraser
    $('#board').on('click', '.square-55d63', function() {
        const square = $(this).data('square');
        const currentPos = board.position();

        if (trashMode) {
            // Eraser mode - remove piece
            if (currentPos[square]) {
                const newPos = {...currentPos};
                delete newPos[square];
                board.position(newPos);
                updateFEN();
                showToast('🧹 Piece erased!', 'success');
            }
        } else if (selectedPiece) {
            // Place piece mode
            const newPos = {...currentPos};
            newPos[square] = selectedPiece;
            board.position(newPos);
            updateFEN();
        }
    });

    $('#copyFenBtn').on('click', function() {
        const fen = $('#fenDisplay').text();
        navigator.clipboard.writeText(fen).then(function() {
            showToast('FEN copied to clipboard!', 'success');
        });
    });

    // Generate game link
    $('#generateLinkBtn').on('click', function() {
        // Check if color is selected
        if (!selectedColor) {
            showToast('Please select a color first!', 'warning');
            return;
        }

        const fen = $('#fenDisplay').text();
        const btn = $(this);
        const originalText = btn.html();
        btn.prop('disabled', true).html('⏳ Generating...');

        $.ajax({
            url: '/editor/generate-game-link/',
            method: 'POST',
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            data: JSON.stringify({
                fen: fen,
                color: selectedColor
            }),
            success: function(response) {
                if (response.success) {
                    $('#gameLinkInput').val(response.game_url);
                    $('#openGameBtn').attr('href', response.game_url);
                    $('#gameLinkSection').removeClass('hidden').hide().slideDown(300);
                    showToast('🎉 Game link generated successfully!', 'success');
                }
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.message || 'Failed to generate link';
                showToast('❌ ' + error, 'error');
            },
            complete: function() {
                btn.prop('disabled', false).html(originalText);
            }
        });
    });

    $('#copyLinkBtn').on('click', function() {
        const link = $('#gameLinkInput').val();
        navigator.clipboard.writeText(link).then(function() {
            showToast('Link copied to clipboard!');
        });
    });

    // Save position (admin only)
    $('#savePositionBtn').on('click', function() {
        // Load topics first
        $.ajax({
            url: '/editor/topics-list/',
            method: 'GET',
            success: function(response) {
                if (response.success) {
                    const select = $('#topicSelect');
                    select.empty().append('<option value="">Select a topic...</option>');
                    response.topics.forEach(function(topic) {
                        select.append(`<option value="${topic.id}">${topic.lesson_title} - ${topic.title}</option>`);
                    });
                    $('#saveModal').removeClass('hidden').addClass('flex');
                }
            },
            error: function(xhr) {
                showToast('❌ Failed to load topics', 'error');
            }
        });
    });

    $('.modal-close').on('click', function() {
        $('#saveModal').removeClass('flex').addClass('hidden');
    });

    // Close modal on outside click
    $('#saveModal').on('click', function(e) {
        if (e.target === this) {
            $(this).removeClass('flex').addClass('hidden');
        }
    });

    $('#savePositionForm').on('submit', function(e) {
        e.preventDefault();

        const data = {
            fen: $('#fenDisplay').text(),
            topic_id: $('#topicSelect').val(),
            description: $('#positionDescription').val(),
            is_sequence_part: $('#isSequencePart').is(':checked')
        };

        $.ajax({
            url: '/editor/save-position/',
            method: 'POST',
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            data: JSON.stringify(data),
            success: function(response) {
                if (response.success) {
                    showToast('✅ Position saved to lesson!', 'success');
                    $('#saveModal').removeClass('flex').addClass('hidden');
                    $('#savePositionForm')[0].reset();
                }
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.message || 'Failed to save position';
                showToast('❌ ' + error, 'error');
            }
        });
    });

    // Utility functions
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function showToast(message, type = 'info') {
        const toast = $('#toast');
        toast.text(message);
        toast.removeClass('hidden');
        toast.css('background', '');

        // Set gradient background based on type
        if (type === 'success') {
            toast.css('background', 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)');
        } else if (type === 'error') {
            toast.css('background', 'linear-gradient(135deg, #ee0979 0%, #ff6a00 100%)');
        } else {
            toast.css('background', 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)');
        }

        toast.addClass('animate-bounce');
        toast.fadeIn(300);

        setTimeout(function() {
            toast.removeClass('animate-bounce');
        }, 500);

        setTimeout(function() {
            toast.fadeOut(300, function() {
                toast.addClass('hidden');
            });
        }, 3500);
    }
})();
