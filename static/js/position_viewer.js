// Position Viewer JavaScript
(function() {
    'use strict';

    let board = null;
    let currentPosition = 0;
    let sequences = [];
    let analysisChess = null;  // Separate chess.js instance for analysis
    let annotations = null;     // Board annotations instance
    let moveHistory = [];       // Track user's exploration moves
    let isSequencePlaying = false; // Track if sequence is active

    // Track selected color for practice
    let selectedColor = null;
    let selectedTurn = 'white'; // Default to white's turn

    // Initialize board after DOM is ready
    $(document).ready(function() {
        console.log('Initializing board with FEN:', STARTING_FEN);

        board = Chessboard('board', {
            position: STARTING_FEN || 'start',
            draggable: true,
            pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
            onDragStart: onDragStart,
            onDrop: onDrop,
            onSnapEnd: onSnapEnd
        });

        // Initialize analysis chess engine
        const fenToUse = STARTING_FEN && STARTING_FEN !== '' ? STARTING_FEN : 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
        console.log('Initializing Chess.js with FEN:', fenToUse);
        analysisChess = new Chess(fenToUse);

        // Define move callback for click-to-move functionality
        function handleClickMove(fromSquare, toSquare) {
            console.log('Click-to-move:', fromSquare, '→', toSquare);

            // Prevent moves during sequence playback
            if (isSequencePlaying) {
                showToast('Cannot move during sequence playback', 'warning');
                return;
            }

            // Try to make the move
            const move = analysisChess.move({
                from: fromSquare,
                to: toSquare,
                promotion: 'q' // Always promote to queen for simplicity
            });

            // Illegal move
            if (move === null) {
                console.log('Illegal move attempted');
                showToast('Illegal move!', 'warning');
                if (annotations) {
                    annotations.clearSelection();
                }
                return;
            }

            // Move successful
            console.log('Move made:', move.san);
            board.position(analysisChess.fen());

            // Add to move history
            moveHistory.push(move);
            updateAnalysisDisplay();
            updateUndoResetButtons();

            // Clear selection after move
            if (annotations) {
                annotations.clearSelection();
            }
        }

        // Initialize board annotations - wait for board to fully render
        setTimeout(function() {
            console.log('Initializing BoardAnnotations with Chess instance:', analysisChess);
            annotations = new BoardAnnotations('board', analysisChess, handleClickMove);
            console.log('BoardAnnotations initialized:', annotations);
        }, 500);

        // Load sequences from template (now with tree structure)
        console.log('SEQUENCES:', SEQUENCES);
        if (typeof SEQUENCES !== 'undefined' && SEQUENCES.length > 0) {
            sequences = SEQUENCES;
            console.log('Rendering sequence tree with', sequences.length, 'sequences');
            renderSequenceTree();
        } else {
            console.log('No sequences to display');
        }

        // Initialize analysis display
        updateAnalysisDisplay();
        updateUndoResetButtons();

        // Color selection handler
        $('.color-choice').on('click', function() {
            const color = $(this).data('color');
            selectedColor = color;

            // Update UI
            $('.color-choice').removeClass('selected');
            $(this).addClass('selected');

            // Enable practice button
            const practiceBtn = $('#practiceBtn');
            practiceBtn.prop('disabled', false);
            practiceBtn.css({
                'opacity': '1',
                'cursor': 'pointer'
            });
        });

        // Turn selection handler
        $('.turn-choice').on('click', function() {
            const turn = $(this).data('turn');
            selectedTurn = turn;

            // Update UI
            $('.turn-choice').removeClass('selected');
            $(this).addClass('selected');
        });

        // Set default turn selection (white)
        $('.turn-choice[data-turn="white"]').addClass('selected');
    });

    // Drag and drop handlers for analysis mode
    function onDragStart(source, piece, position, orientation) {
        // Keep legal move indicators visible during drag
        // They will be cleared after move completion or reset

        // Prevent dragging during sequence playback
        if (isSequencePlaying) {
            return false;
        }

        // Prevent dragging if game is over
        if (analysisChess.game_over()) {
            return false;
        }

        // Only allow dragging pieces of the correct color
        if ((analysisChess.turn() === 'w' && piece.search(/^b/) !== -1) ||
            (analysisChess.turn() === 'b' && piece.search(/^w/) !== -1)) {
            return false;
        }
    }

    function onDrop(source, target) {
        // Prevent moves during sequence playback
        if (isSequencePlaying) {
            return 'snapback';
        }

        // If dropped on same square, just cancel (this happens with quick clicks)
        if (source === target) {
            console.log('Dropped on same square - canceling');
            return 'snapback';
        }

        // Try to make the move
        const move = analysisChess.move({
            from: source,
            to: target,
            promotion: 'q' // Always promote to queen for simplicity
        });

        // Illegal move
        if (move === null) {
            return 'snapback';
        }

        // Add to move history
        moveHistory.push(move);
        updateAnalysisDisplay();
        updateUndoResetButtons();

        // Clear selection after successful drag move
        if (annotations) {
            annotations.clearSelection();
        }
    }

    function onSnapEnd() {
        // Update board to match chess.js position
        board.position(analysisChess.fen());
    }

    // Analysis mode functions
    function undoMove() {
        if (moveHistory.length === 0) return;

        analysisChess.undo();
        moveHistory.pop();
        board.position(analysisChess.fen());
        updateAnalysisDisplay();
        updateUndoResetButtons();

        // Clear selection when undoing
        if (annotations) {
            annotations.clearSelection();
        }

        showToast('Move undone', 'info');
    }

    function resetAnalysis() {
        analysisChess.load(STARTING_FEN);
        moveHistory = [];
        board.position(STARTING_FEN);
        updateAnalysisDisplay();
        updateUndoResetButtons();

        // Clear selection when resetting
        if (annotations) {
            annotations.clearSelection();
        }

        showToast('Position reset', 'info');
    }

    function updateAnalysisDisplay() {
        const moveListDiv = $('#analysisMoveList');
        if (moveHistory.length === 0) {
            moveListDiv.html('<p class="text-gray-500 text-sm italic">No moves yet - drag pieces to explore!</p>');
            return;
        }

        // Format moves in pairs (white, black)
        let html = '<div class="space-y-1">';
        for (let i = 0; i < moveHistory.length; i += 2) {
            const moveNum = Math.floor(i / 2) + 1;
            const whiteMove = moveHistory[i].san;
            const blackMove = moveHistory[i + 1] ? moveHistory[i + 1].san : '';

            html += `<div class="flex gap-2">
                <span class="font-medium text-gray-600">${moveNum}.</span>
                <span class="font-mono">${whiteMove}</span>
                ${blackMove ? `<span class="font-mono">${blackMove}</span>` : ''}
            </div>`;
        }
        html += '</div>';
        moveListDiv.html(html);
    }

    function updateUndoResetButtons() {
        const hasHistory = moveHistory.length > 0;
        $('#undoMoveBtn').prop('disabled', !hasHistory || isSequencePlaying);
        $('#resetAnalysisBtn').prop('disabled', !hasHistory || isSequencePlaying);

        // Update button appearance
        if (hasHistory && !isSequencePlaying) {
            $('#undoMoveBtn').removeClass('opacity-50 cursor-not-allowed');
            $('#resetAnalysisBtn').removeClass('opacity-50 cursor-not-allowed');
        } else {
            $('#undoMoveBtn').addClass('opacity-50 cursor-not-allowed');
            $('#resetAnalysisBtn').addClass('opacity-50 cursor-not-allowed');
        }
    }

    // Tree structure functions for variations
    function buildSequenceTree(sequences) {
        // Build tree from flat sequence list
        const root = { children: [] };
        const nodeMap = {};

        // Sort sequences by order and variation
        const sorted = [...sequences].sort((a, b) => {
            if (a.sequence_order !== b.sequence_order) {
                return a.sequence_order - b.sequence_order;
            }
            return a.variation_number - b.variation_number;
        });

        // Create nodes
        for (const seq of sorted) {
            const node = {
                id: seq.id,
                order: seq.sequence_order,
                move: seq.move_san,
                explanation: seq.explanation,
                parent_id: seq.parent_move_id,
                variation_number: seq.variation_number,
                children: []
            };
            nodeMap[seq.id] = node;

            if (!seq.parent_move_id) {
                root.children.push(node);
            } else if (nodeMap[seq.parent_move_id]) {
                nodeMap[seq.parent_move_id].children.push(node);
            }
        }

        return root;
    }

    function renderSequenceTree() {
        const tree = buildSequenceTree(sequences);
        const html = renderTreeNodes(tree.children, 0, 1);
        $('#sequenceList').html(html);

        // Add click handlers for variations
        $('.sequence-item').on('click', function() {
            const moveId = $(this).data('move-id');
            console.log('Sequence item clicked, moveId:', moveId);
            navigateToMove(moveId);
        });

        // Show variations toggle
        $('#showVariationsToggle').on('change', function() {
            if ($(this).is(':checked')) {
                $('.variation-item').show();
            } else {
                $('.variation-item').hide();
            }
        });
    }

    function renderTreeNodes(nodes, depth, moveNum) {
        let html = '';
        let currentMoveNum = moveNum;

        for (let i = 0; i < nodes.length; i++) {
            const node = nodes[i];
            const isMainLine = node.variation_number === 0;
            const isVariation = !isMainLine;
            const indent = depth * 20;

            // Determine move number display
            const isWhiteMove = currentMoveNum % 2 === 1;
            const displayNum = Math.ceil(currentMoveNum / 2);
            const movePrefix = isWhiteMove ? `${displayNum}.` : `${displayNum}...`;

            const itemClass = isVariation ? 'sequence-item variation-item' : 'sequence-item main-line-item';
            const bgColor = isVariation ? 'var(--gray-50)' : 'transparent';
            const borderLeft = isVariation ? '3px solid var(--accent)' : 'none';

            html += `
                <div class="${itemClass}"
                     data-move-id="${node.id}"
                     data-move="${node.move}"
                     data-order="${node.order}"
                     style="margin-left: ${indent}px; padding: var(--space-3); background: ${bgColor}; border-radius: var(--radius-sm); border-left: ${borderLeft}; cursor: pointer; transition: all 0.2s ease;"
                     onmouseover="this.style.background='var(--gray-100)'"
                     onmouseout="this.style.background='${bgColor}'">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2);">
                        <span class="badge badge-gold">
                            ${isVariation ? '↳ ' : ''}${movePrefix} ${node.move}
                        </span>
                        <span class="sequence-status" style="color: var(--text-tertiary);">⏸</span>
                    </div>
                    <p style="font-size: var(--text-sm); color: var(--text-secondary); line-height: var(--line-height-relaxed);">
                        ${node.explanation || '<em>No explanation</em>'}
                    </p>
                </div>
            `;

            // Recursively render children
            if (node.children.length > 0) {
                html += renderTreeNodes(node.children, depth + 1, currentMoveNum + 1);
            }

            // Only increment move number for main line
            if (isMainLine) {
                currentMoveNum++;
            }
        }

        return html;
    }

    function navigateToMove(moveId) {
        console.log('navigateToMove called with moveId:', moveId);

        // Find the path to this move
        const path = findPathToMove(moveId);
        console.log('Path found:', path);

        if (!path) {
            console.error('No path found for moveId:', moveId);
            return;
        }

        // Reset to starting position
        const fenToUse = STARTING_FEN && STARTING_FEN !== '' ? STARTING_FEN : 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
        console.log('Resetting to FEN:', fenToUse);

        analysisChess.load(fenToUse);
        moveHistory = [];
        board.position(fenToUse);

        // Play moves to reach this position
        let currentChess = new Chess(fenToUse);
        for (const node of path) {
            console.log('Playing move:', node.move);
            try {
                const move = currentChess.move(node.move, { sloppy: true });
                if (move) {
                    console.log('Move successful:', move.san);
                    const analysisMove = analysisChess.move(node.move, { sloppy: true });
                    if (analysisMove) {
                        moveHistory.push(analysisMove);
                    }
                } else {
                    console.error('Move failed:', node.move);
                }
            } catch (e) {
                console.error(`Error navigating to move ${node.move}:`, e);
                showToast(`Error navigating to move: ${node.move}`, 'error');
                return;
            }
        }

        // Update board and display
        const finalFen = analysisChess.fen();
        console.log('Setting board to final FEN:', finalFen);
        board.position(finalFen);
        updateAnalysisDisplay();
        updateUndoResetButtons();

        // Highlight the selected move
        $('.sequence-item').removeClass('active');
        $(`.sequence-item[data-move-id="${moveId}"]`).addClass('active');

        showToast(`Navigated to move: ${path[path.length - 1].move}`, 'info');
    }

    function findPathToMove(moveId, nodes = null, path = []) {
        if (nodes === null) {
            const tree = buildSequenceTree(sequences);
            nodes = tree.children;
        }

        for (const node of nodes) {
            const currentPath = [...path, node];

            if (node.id == moveId) {
                return currentPath;
            }

            if (node.children.length > 0) {
                const found = findPathToMove(moveId, node.children, currentPath);
                if (found) return found;
            }
        }

        return null;
    }

    // Mark complete button
    $('#completeBtn').on('click', function() {
        const btn = $(this);
        if (btn.prop('disabled')) return;

        btn.prop('disabled', true);

        $.ajax({
            url: `/lessons/position/${POSITION_ID}/complete/`,
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            success: function(response) {
                if (response.success) {
                    btn.text('✓ Completed');
                    btn.addClass('opacity-50 cursor-not-allowed');
                    showToast('Position marked as complete!', 'success');
                }
            },
            error: function(xhr) {
                btn.prop('disabled', false);
                showToast('Failed to mark complete', 'error');
            }
        });
    });

    // Practice button
    $('#practiceBtn').on('click', function() {
        const btn = $(this);

        // Check if color is selected
        if (!selectedColor) {
            showToast('Please select a color first!', 'warning');
            return;
        }

        btn.prop('disabled', true).text('Creating game...');

        // Get current FEN from analysis chess instance
        let currentFen = analysisChess.fen();

        // Modify FEN to set the starting turn
        const fenParts = currentFen.split(' ');
        fenParts[1] = selectedTurn === 'white' ? 'w' : 'b';
        currentFen = fenParts.join(' ');

        $.ajax({
            url: `/lessons/position/${POSITION_ID}/practice/`,
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            data: JSON.stringify({
                color: selectedColor,
                current_fen: currentFen
            }),
            success: function(response) {
                if (response.success) {
                    window.open(response.game_url, '_blank');
                    showToast('Practice game created!', 'success');
                }
            },
            error: function(xhr) {
                showToast('Failed to create practice game', 'error');
            },
            complete: function() {
                btn.prop('disabled', false).text('🎮 Practice from this Position');
            }
        });
    });

    // Undo move button
    $('#undoMoveBtn').on('click', function() {
        undoMove();
    });

    // Reset analysis button
    $('#resetAnalysisBtn').on('click', function() {
        resetAnalysis();
    });

    // Play sequence button
    $('#playSequenceBtn').on('click', function() {
        if (sequences.length === 0) return;

        // Disable analysis mode during sequence playback
        isSequencePlaying = true;

        // Reset to starting position
        resetAnalysis();

        $(this).addClass('hidden');
        $('#resetSequenceBtn').removeClass('hidden');

        playSequence();
    });

    $('#resetSequenceBtn').on('click', function() {
        board.position(STARTING_FEN);
        currentPosition = 0;
        $('.sequence-item').removeClass('active completed');
        $('.sequence-status').text('⏸');

        // Re-enable analysis mode
        isSequencePlaying = false;
        resetAnalysis();

        $(this).addClass('hidden');
        $('#playSequenceBtn').removeClass('hidden');
    });

    async function playSequence() {
        // Get main line only (variation_number === 0)
        const mainLine = getMainLine();

        if (mainLine.length === 0) {
            showToast('No main line found', 'warning');
            return;
        }

        // Initialize chess engine with starting position
        const chess = new Chess(STARTING_FEN);

        for (let i = 0; i < mainLine.length; i++) {
            await sleep(1500);

            const node = mainLine[i];
            const item = $(`.sequence-item[data-move-id="${node.id}"]`);

            // Highlight current move
            $('.sequence-item').removeClass('active');
            item.addClass('active');
            item.find('.sequence-status').text('▶️');

            // Apply move to chess engine and update board
            try {
                const move = chess.move(node.move, { sloppy: true });
                if (move) {
                    // Update visual board with new position
                    board.position(chess.fen());
                } else {
                    console.error(`Invalid move: ${node.move}`);
                    showToast(`Invalid move: ${node.move}`, 'error');
                }
            } catch (e) {
                console.error(`Error applying move ${node.move}:`, e);
                showToast(`Error applying move: ${node.move}`, 'error');
            }

            await sleep(1000);
            item.addClass('completed');
            item.find('.sequence-status').text('✓');
        }

        showToast('Sequence completed!', 'success');

        // Apply all sequence moves to analysis chess and move history
        analysisChess.load(STARTING_FEN);
        moveHistory = [];

        for (const node of mainLine) {
            try {
                const move = analysisChess.move(node.move, { sloppy: true });
                if (move) {
                    moveHistory.push(move);
                }
            } catch (e) {
                console.error(`Error applying move to analysis: ${node.move}`, e);
            }
        }

        // Update analysis display with sequence moves
        updateAnalysisDisplay();

        // Re-enable analysis mode
        isSequencePlaying = false;
        updateUndoResetButtons();
    }

    function getMainLine() {
        // Extract main line (variation_number === 0) from tree
        const tree = buildSequenceTree(sequences);
        const mainLine = [];

        function traverseMainLine(nodes) {
            for (const node of nodes) {
                if (node.variation_number === 0) {
                    mainLine.push(node);
                    if (node.children.length > 0) {
                        traverseMainLine(node.children);
                    }
                    break; // Only follow first main line move
                }
            }
        }

        traverseMainLine(tree.children);
        return mainLine;
    }

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

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
        toast.removeClass('hidden bg-blue-500 bg-green-500 bg-red-500');

        if (type === 'success') {
            toast.addClass('bg-green-500');
        } else if (type === 'error') {
            toast.addClass('bg-red-500');
        } else {
            toast.addClass('bg-blue-500');
        }

        toast.fadeIn();
        setTimeout(function() {
            toast.fadeOut();
        }, 3000);
    }
})();
