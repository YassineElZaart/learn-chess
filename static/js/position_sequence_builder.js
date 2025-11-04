/**
 * Position Sequence Builder
 * Manages move sequences with branching variations for chess positions
 */

class PositionSequenceBuilder {
    constructor(boardElementId, sidebarElementId, initialFen = 'start') {
        this.boardElementId = boardElementId;
        this.sidebarElementId = sidebarElementId;
        this.initialFen = initialFen;

        // Chess.js instance for move validation
        this.chess = new Chess(initialFen);

        // Move tree structure
        this.moveTree = {
            root: true,
            fen: initialFen,
            children: []  // Array of move nodes
        };

        this.currentNode = this.moveTree;
        this.mode = 'setup';  // 'setup' or 'sequence'
        this.board = null;
        this.selectedMoveId = null;
        this.collapsedMoves = new Set();  // Track which moves have their children collapsed

        // Setup mode state
        this.selectedPiece = null;
        this.trashMode = false;
        this.currentTurn = 'white';

        this.initializeBoard();
        this.initializeEventListeners();
        this.initializePieceSelector();
    }

    initializeBoard() {
        const config = {
            draggable: true,
            sparePieces: false,
            dropOffBoard: 'trash',
            position: this.initialFen === 'start' ? 'start' : this.initialFen,
            pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
            onDrop: this.handleDrop.bind(this)  // Use wrapper that checks mode dynamically
        };

        this.board = Chessboard(this.boardElementId, config);

        // Resize board to fit container properly
        window.addEventListener('resize', () => {
            this.board.resize();
        });

        // Sync board with chess.js
        if (this.initialFen !== 'start') {
            this.board.position(this.initialFen);
        }
    }

    handleDrop(source, target, piece, newPos, oldPos, orientation) {
        // Delegate to appropriate handler based on current mode
        if (this.mode === 'setup') {
            return this.onPieceDrop(source, target, piece, newPos, oldPos, orientation);
        } else {
            return this.onMoveAttempt(source, target);
        }
    }

    initializeEventListeners() {
        // Mode toggle buttons
        document.getElementById('mode-setup')?.addEventListener('click', () => this.switchMode('setup'));
        document.getElementById('mode-sequence')?.addEventListener('click', () => this.switchMode('sequence'));

        // Board controls
        document.getElementById('clearBtn')?.addEventListener('click', () => this.clearBoard());
        document.getElementById('startBtn')?.addEventListener('click', () => this.resetBoard());
        document.getElementById('flipBtn')?.addEventListener('click', () => this.board.flip());

        // Turn toggle buttons
        document.getElementById('whiteTurnBtn')?.addEventListener('click', () => this.setTurn('white'));
        document.getElementById('blackTurnBtn')?.addEventListener('click', () => this.setTurn('black'));

        // Export/Import
        document.getElementById('export-json')?.addEventListener('click', () => this.exportToJSON());

        // Add variation buttons (dynamically created)
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('add-variation-btn')) {
                const moveId = e.target.dataset.moveId;
                this.addVariation(moveId);
            }
        });
    }

    initializePieceSelector() {
        // Piece selector buttons
        document.querySelectorAll('.piece-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const piece = e.currentTarget.dataset.piece;
                this.selectedPiece = piece;
                this.trashMode = false;
                this.updatePieceButtonStates();
            });
        });

        // Eraser/trash button
        document.getElementById('trashBtn')?.addEventListener('click', () => {
            this.trashMode = true;
            this.selectedPiece = null;
            this.updatePieceButtonStates();
        });

        // Board click handler for setup mode
        const boardElement = document.getElementById(this.boardElementId);
        if (boardElement) {
            boardElement.addEventListener('click', (e) => {
                if (this.mode !== 'setup') return;

                // Find which square was clicked
                const square = this.getSquareFromEvent(e);
                if (square) {
                    this.handleBoardClick(square);
                }
            });
        }
    }

    updatePieceButtonStates() {
        // Remove active class from all buttons
        document.querySelectorAll('.piece-btn, #trashBtn').forEach(btn => {
            btn.classList.remove('active');
        });

        // Add active class to selected button
        if (this.trashMode) {
            document.getElementById('trashBtn')?.classList.add('active');
        } else if (this.selectedPiece) {
            document.querySelectorAll('.piece-btn').forEach(btn => {
                if (btn.dataset.piece === this.selectedPiece) {
                    btn.classList.add('active');
                }
            });
        }
    }

    getSquareFromEvent(e) {
        // Find the square element that was clicked
        let target = e.target;
        while (target && !target.dataset.square) {
            target = target.parentElement;
        }
        return target ? target.dataset.square : null;
    }

    handleBoardClick(square) {
        if (this.mode !== 'setup') return;

        const currentPos = this.board.position();

        if (this.trashMode) {
            // Remove piece from square
            delete currentPos[square];
        } else if (this.selectedPiece) {
            // Place selected piece on square
            currentPos[square] = this.selectedPiece;
        }

        this.board.position(currentPos);
    }

    setTurn(turn) {
        this.currentTurn = turn;

        // Update button states
        document.querySelectorAll('.turn-btn').forEach(btn => {
            btn.classList.remove('active');
        });

        if (turn === 'white') {
            document.getElementById('whiteTurnBtn')?.classList.add('active');
        } else {
            document.getElementById('blackTurnBtn')?.classList.add('active');
        }

        // If in setup mode and board exists, update chess.js with new turn
        // This ensures turn changes are reflected in FEN
        if (this.mode === 'setup' && this.board) {
            const fen = this.getFEN();
            this.chess = new Chess(fen);
        }
    }

    switchMode(mode) {
        this.mode = mode;

        // Update UI
        document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
        document.getElementById(`mode-${mode}`).classList.add('active');

        // Find piece selector
        const pieceSelector = document.querySelector('.piece-selector');

        if (mode === 'setup') {
            // Enable piece placement
            this.board.draggable = true;

            // Show piece selector
            if (pieceSelector) {
                pieceSelector.style.display = 'block';
            }

            // Show sequence sidebar content but with empty state
            const sidebar = document.getElementById(this.sidebarElementId);
            if (sidebar) {
                const contentDiv = sidebar.querySelector('.sequence-content');
                if (contentDiv) {
                    contentDiv.innerHTML = '<p style="font-size: var(--text-sm); opacity: 0.7;">Switch to "Build Sequence" mode to start recording moves.</p>';
                }
            }
        } else {
            // Enable move making
            this.initializeSequenceMode();

            // Hide piece selector
            if (pieceSelector) {
                pieceSelector.style.display = 'none';
            }
        }
    }

    initializeSequenceMode() {
        // Build complete FEN with turn information
        const position = this.board.fen();
        const turn = this.currentTurn === 'white' ? 'w' : 'b';
        const fen = `${position} ${turn} KQkq - 0 1`;

        this.chess = new Chess(fen);
        this.initialFen = fen;

        // Reset move tree with new starting position
        if (this.moveTree.children.length === 0) {
            this.moveTree.fen = fen;
            this.currentNode = this.moveTree;
        }

        this.renderSequenceSidebar();
    }

    onPieceDrop(source, target, piece, newPos, oldPos, orientation) {
        // In setup mode, allow free piece placement
        return true;
    }

    onMoveAttempt(source, target) {
        // In sequence mode, validate and record moves
        const move = this.chess.move({
            from: source,
            to: target,
            promotion: 'q'  // Always promote to queen for now
        });

        if (move === null) return 'snapback';

        // Check if this move already exists in current node's children
        const existingMove = this.currentNode.children.find(child => child.san === move.san);

        if (existingMove) {
            // Move already exists - navigate to it instead of creating duplicate
            this.navigateToMove(existingMove.id);
            this.selectedMoveId = existingMove.id;

            // Re-render and update states
            this.renderSequenceSidebar();
            this.updateMoveStates();

            // Update board
            this.board.position(this.chess.fen());

            return true;
        }

        // Add new move to tree (as main line or variation)
        this.addMoveToTree(move);

        // Update board
        this.board.position(this.chess.fen());

        return true;
    }

    addMoveToTree(move) {
        // Calculate variation number: 0 for main line, 1+ for variations
        const variationNumber = this.currentNode.children.length;

        const moveNode = {
            id: this.generateMoveId(),
            moveNumber: this.chess.history().length,
            san: move.san,
            fen: this.chess.fen(),
            explanation: '',
            parentId: this.currentNode.root ? null : this.currentNode.id,
            variationNumber: variationNumber,
            children: []
        };

        this.currentNode.children.push(moveNode);
        this.currentNode = moveNode;
        this.selectedMoveId = moveNode.id;

        this.renderSequenceSidebar();
        this.updateMoveStates();
        this.promptForExplanation(moveNode.id);
    }

    addVariation(parentMoveId) {
        // Find parent node
        const parentNode = this.findMoveNode(parentMoveId);
        if (!parentNode) return;

        // Set board to parent position
        this.navigateToMove(parentMoveId);

        // Indicate variation mode
        alert('Make a move to create a variation from move ' + parentNode.san);
    }

    findMoveNode(moveId, node = this.moveTree) {
        if (node.id === moveId) return node;

        for (const child of node.children || []) {
            const found = this.findMoveNode(moveId, child);
            if (found) return found;
        }

        return null;
    }

    navigateToMove(moveId) {
        // Reset to start
        this.chess = new Chess(this.initialFen);

        // Get move path
        const path = this.getMovePathToNode(moveId);

        console.log(`Navigating to move ${moveId}, path length: ${path?.length || 0}`);

        // Play moves to reach position
        for (const move of path) {
            this.chess.move(move.san);
        }

        // Update board position and force refresh
        const newFen = this.chess.fen();
        console.log(`Setting board to FEN: ${newFen}`);
        this.board.position(newFen, false);  // false = no animation for instant update

        this.currentNode = this.findMoveNode(moveId);
        console.log(`Current node updated to: ${this.currentNode?.san || 'root'}`);
    }

    getMovePathToNode(moveId, node = this.moveTree, path = []) {
        if (node.id === moveId) return path;

        for (const child of node.children || []) {
            const childPath = [...path, child];
            const found = this.getMovePathToNode(moveId, child, childPath);
            if (found) return found;
        }

        return null;
    }

    promptForExplanation(moveId) {
        // Auto-expand and focus the explanation for newly added moves
        const move = this.findMoveNode(moveId);
        if (!move) return;

        // Expand the description
        this.toggleMoveDescription(moveId);

        // Scroll within the sidebar only (not the whole page)
        const textarea = document.querySelector(`textarea[data-move-id="${moveId}"]`);
        const sidebar = document.getElementById(this.sidebarElementId);

        if (textarea && sidebar) {
            // Get positions relative to sidebar
            const sidebarRect = sidebar.getBoundingClientRect();
            const textareaRect = textarea.getBoundingClientRect();

            // Only scroll if textarea is not fully visible in sidebar
            if (textareaRect.bottom > sidebarRect.bottom || textareaRect.top < sidebarRect.top) {
                // Scroll sidebar container, not the whole page
                const scrollTop = textarea.offsetTop - sidebar.offsetTop - 100;
                sidebar.scrollTo({
                    top: scrollTop,
                    behavior: 'smooth'
                });
            }
        }
    }

    updateExplanation(moveId, explanation) {
        const move = this.findMoveNode(moveId);
        if (move) {
            move.explanation = explanation;
        }
    }

    deleteMove(moveId) {
        // Find the move and count descendants
        const move = this.findMoveNode(moveId);
        if (!move) return;

        const descendantCount = this.countDescendants(move);

        // Confirm deletion if there are variations
        if (descendantCount > 0) {
            const plural = descendantCount === 1 ? 'variation' : 'variations';
            if (!confirm(`Delete this move and ${descendantCount} ${plural} branching from it?`)) {
                return;
            }
        }

        // Find and remove move from tree (this cascades to all children)
        const parent = this.findParentNode(moveId);
        if (!parent) return;

        parent.children = parent.children.filter(child => child.id !== moveId);

        // Navigate back to parent position
        if (parent.root) {
            this.chess = new Chess(this.initialFen);
            this.board.position(this.initialFen);
            this.currentNode = this.moveTree;
        } else {
            this.navigateToMove(parent.id);
        }

        this.selectedMoveId = parent.root ? null : parent.id;
        this.renderSequenceSidebar();
        this.updateMoveStates();
    }

    countDescendants(node) {
        // Count all descendants recursively
        let count = 0;
        for (const child of node.children || []) {
            count += 1 + this.countDescendants(child);
        }
        return count;
    }

    deleteAllSequences() {
        // Clear entire sequence tree
        if (this.moveTree.children.length === 0) return;

        if (confirm('Delete all moves and variations? This cannot be undone.')) {
            this.moveTree.children = [];
            this.chess = new Chess(this.initialFen);
            this.board.position(this.initialFen);
            this.currentNode = this.moveTree;
            this.selectedMoveId = null;
            this.renderSequenceSidebar();
        }
    }

    findParentNode(moveId, node = this.moveTree) {
        for (const child of node.children || []) {
            if (child.id === moveId) return node;
            const found = this.findParentNode(moveId, child);
            if (found) return found;
        }
        return null;
    }

    renderSequenceSidebar() {
        const sidebar = document.getElementById(this.sidebarElementId);
        if (!sidebar) return;

        // Show/hide Clear All button
        const clearBtn = document.getElementById('clear-sequences-btn');
        if (clearBtn) {
            clearBtn.style.display = this.moveTree.children.length > 0 ? 'flex' : 'none';
        }

        // Find or create content div
        let contentDiv = sidebar.querySelector('.sequence-content');
        if (!contentDiv) {
            contentDiv = document.createElement('div');
            contentDiv.className = 'sequence-content';
            sidebar.appendChild(contentDiv);
        }

        if (this.moveTree.children.length === 0) {
            contentDiv.innerHTML = '<p class="text-muted" style="margin-top: var(--space-4);">No moves yet. Switch to "Build Sequence" mode and make moves on the board.</p>';
            return;
        }

        const treeHtml = this.renderMoveTree(this.moveTree);
        contentDiv.innerHTML = treeHtml;
    }

    renderMoveTree(node, depth = 0, moveNumber = 1) {
        let html = '';

        for (let i = 0; i < node.children.length; i++) {
            const move = node.children[i];
            const isMainLine = i === 0;
            const isVariation = i > 0;
            const indent = depth * 20;

            // Check if this move has children and is collapsed
            const hasChildren = move.children.length > 0;
            const isCollapsed = this.collapsedMoves.has(move.id);

            // Visual styling based on line type
            const borderColor = isMainLine ? 'var(--royal-gold-500)' : '#4a9eff';
            const variationBadge = isVariation ? `<span style="background: #4a9eff; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; margin-right: 8px;">Alt ${i}</span>` : '';

            // Collapse/expand icon (only show if move has children)
            const collapseIcon = hasChildren ? `
                <svg width="12" height="12" fill="currentColor" viewBox="0 0 16 16"
                     class="collapse-icon ${isCollapsed ? 'collapsed' : ''}"
                     onclick="sequenceBuilder.toggleMoveCollapse('${move.id}', event)"
                     style="cursor: pointer; margin-right: 6px;">
                    <path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708.708l-6 6a.5.5 0 0 1-.708 0l-6-6a.5.5 0 0 1 0-.708z"/>
                </svg>
            ` : '<span style="display: inline-block; width: 18px;"></span>';

            // Description expand icon (for the textarea)
            const descriptionIcon = `
                <svg width="12" height="12" fill="currentColor" viewBox="0 0 16 16"
                     class="expand-icon"
                     data-move-id="${move.id}"
                     onclick="sequenceBuilder.toggleMoveDescription('${move.id}'); event.stopPropagation();"
                     style="cursor: pointer; margin-right: 8px;">
                    <path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708.708l-6 6a.5.5 0 0 1-.708 0l-6-6a.5.5 0 0 1 0-.708z"/>
                </svg>
            `;

            html += `
                <div class="move-item ${hasChildren ? 'has-children' : ''}"
                     style="margin-left: ${indent}px; border-left-color: ${borderColor};"
                     data-move-id="${move.id}">
                    <div class="move-header" onclick="sequenceBuilder.onMoveHeaderClick('${move.id}')" style="cursor: pointer;">
                        ${collapseIcon}
                        ${variationBadge}
                        <span class="move-number">${Math.ceil(moveNumber / 2)}${moveNumber % 2 === 1 ? '.' : '...'}</span>
                        <span class="move-san">${move.san}</span>
                        ${descriptionIcon}
                        <div class="move-actions" onclick="event.stopPropagation();">
                            <button class="btn-icon delete-move-btn" onclick="sequenceBuilder.deleteMove('${move.id}')" title="Delete this move">
                                <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                                    <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/>
                                    <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    <textarea
                        class="move-explanation collapsed"
                        data-move-id="${move.id}"
                        placeholder="Click to add explanation..."
                        onchange="sequenceBuilder.updateExplanation('${move.id}', this.value)"
                        onclick="event.stopPropagation();"
                    >${move.explanation || ''}</textarea>
                </div>
            `;

            // Render children if not collapsed
            if (hasChildren && !isCollapsed) {
                html += this.renderMoveTree(move, depth + 1, moveNumber + 1);
            }
        }

        return html;
    }

    toggleMoveDescription(moveId) {
        // Find the textarea and expand icon for this move
        const textarea = document.querySelector(`textarea.move-explanation[data-move-id="${moveId}"]`);
        const icon = document.querySelector(`.expand-icon[data-move-id="${moveId}"]`);

        if (textarea && icon) {
            const isCollapsed = textarea.classList.contains('collapsed');

            if (isCollapsed) {
                // Expand
                textarea.classList.remove('collapsed');
                icon.style.transform = 'rotate(180deg)';
                textarea.focus();
            } else {
                // Collapse
                textarea.classList.add('collapsed');
                icon.style.transform = 'rotate(0deg)';
            }
        }
    }

    toggleMoveCollapse(moveId, event) {
        // Stop propagation to prevent triggering onMoveHeaderClick
        if (event) {
            event.stopPropagation();
        }

        // Toggle collapsed state
        if (this.collapsedMoves.has(moveId)) {
            this.collapsedMoves.delete(moveId);  // Expand
        } else {
            this.collapsedMoves.add(moveId);     // Collapse
        }

        // Re-render tree to show/hide children
        this.renderSequenceSidebar();

        // Restore visual state after re-render
        this.updateMoveStates();
    }

    onMoveHeaderClick(moveId) {
        console.log(`Move header clicked: ${moveId}`);

        // Navigate to this position
        this.navigateToMove(moveId);

        // Update selected move tracking
        this.selectedMoveId = moveId;

        // Update visual states
        this.updateMoveStates();

        // Expand description if collapsed
        const textarea = document.querySelector(`textarea.move-explanation[data-move-id="${moveId}"]`);
        const icon = document.querySelector(`.expand-icon[data-move-id="${moveId}"]`);

        if (textarea && icon && textarea.classList.contains('collapsed')) {
            textarea.classList.remove('collapsed');
            icon.style.transform = 'rotate(180deg)';
        }

        console.log(`Board should now show position after move: ${this.currentNode?.san}`);
    }

    updateMoveStates() {
        // Remove active class from all moves
        document.querySelectorAll('.move-item').forEach(item => {
            item.classList.remove('move-active');
        });

        // Add active class to selected move
        if (this.selectedMoveId) {
            const moveItem = document.querySelector(`.move-item[data-move-id="${this.selectedMoveId}"]`);
            if (moveItem) {
                moveItem.classList.add('move-active');
            }
        }
    }

    clearBoard() {
        this.board.clear();
        this.chess = new Chess();
    }

    resetBoard() {
        this.board.start();
        this.chess = new Chess();
    }

    exportToJSON() {
        // Convert tree to flat list for Django model
        const sequences = [];
        this.flattenTreeToSequences(this.moveTree, sequences);

        // Store in hidden form field
        const input = document.getElementById('sequence-data');
        if (input) {
            input.value = JSON.stringify(sequences);
        }

        return sequences;
    }

    flattenTreeToSequences(node, sequences, parentId = null, sequenceOrder = 1) {
        for (let i = 0; i < node.children.length; i++) {
            const move = node.children[i];

            sequences.push({
                id: move.id,  // Include ID for parent mapping
                move_san: move.san,
                explanation: move.explanation,
                parent_move_id: parentId,
                sequence_order: sequenceOrder,
                variation_number: i
            });

            // Recursively process children
            if (move.children.length > 0) {
                this.flattenTreeToSequences(move, sequences, move.id, sequenceOrder + 1);
            }
        }
    }

    importFromJSON(sequencesData) {
        if (!sequencesData || sequencesData.length === 0) {
            console.log('No sequences to import');
            return;
        }

        console.log('Importing sequences:', sequencesData);

        // Sort by sequence_order to ensure correct tree building
        const sorted = [...sequencesData].sort((a, b) => a.sequence_order - b.sequence_order);

        // Build tree structure from flat list
        const idMap = new Map(); // Maps temp IDs to tree nodes
        idMap.set(null, this.moveTree); // Root node

        for (const seq of sorted) {
            const parentNode = idMap.get(seq.parent_move_id) || this.moveTree;

            const moveNode = {
                id: this.generateMoveId(),
                moveNumber: seq.sequence_order,
                san: seq.move_san,
                fen: '',  // Will be calculated
                explanation: seq.explanation || '',
                parentId: seq.parent_move_id,
                variationNumber: seq.variation_number,
                children: []
            };

            parentNode.children.push(moveNode);
            idMap.set(seq.temp_id || moveNode.id, moveNode);
        }

        // Update UI
        this.renderSequenceSidebar();

        console.log('Sequences imported successfully');
    }

    generateMoveId() {
        return 'move_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    getFEN() {
        if (this.mode === 'setup') {
            // board.fen() only returns position, build complete FEN with turn info
            const position = this.board.fen();
            const turn = this.currentTurn === 'white' ? 'w' : 'b';
            // Complete FEN format: position turn castling en-passant halfmove fullmove
            return `${position} ${turn} KQkq - 0 1`;
        } else {
            // In sequence mode, return the STARTING FEN (before any moves), not current position
            return this.initialFen;
        }
    }
}

// Global instance (initialized in template)
let sequenceBuilder = null;
