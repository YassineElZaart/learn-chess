/**
 * Chess Board Annotations Module
 * Provides legal move indicators, circle annotations, and arrow annotations
 * for interactive chess boards
 */

class BoardAnnotations {
    constructor(boardId, chessInstance = null, moveCallback = null) {
        this.boardId = boardId;
        this.chess = chessInstance;
        this.boardElement = document.getElementById(boardId);
        this.annotations = {
            circles: {}, // { 'e4': 'green', 'e5': 'red' }
            arrows: []   // [{ from: 'e2', to: 'e4', color: 'green' }]
        };
        this.colors = ['green', 'red', 'blue', 'yellow'];
        this.currentColor = 0;
        this.legalMovesVisible = false;
        this.arrowDragStart = null;
        this.isDraggingArrow = false;
        this.selectedSquare = null; // Track currently selected piece
        this.moveCallback = moveCallback; // Callback for when user clicks legal move dot

        if (!this.boardElement) {
            console.error(`Board element with id '${boardId}' not found`);
            return;
        }

        this.setupOverlay();
        this.setupEventListeners();
    }

    /**
     * Create SVG overlay for annotations
     */
    setupOverlay() {
        // Remove existing overlay if present
        const existing = document.getElementById('board-annotations-overlay');
        if (existing) {
            existing.remove();
        }

        // Create new SVG overlay
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.id = 'board-annotations-overlay';
        svg.style.position = 'absolute';
        svg.style.top = '0';
        svg.style.left = '0';
        svg.style.width = '100%';
        svg.style.height = '100%';
        svg.style.pointerEvents = 'none'; // Don't capture clicks on empty areas
        svg.style.zIndex = '100';

        // Position SVG directly inside board element, not parent card
        this.boardElement.style.position = 'relative';
        this.boardElement.appendChild(svg);
        this.overlay = svg;
    }

    /**
     * Setup event listeners for clicks and right-clicks
     */
    setupEventListeners() {
        const squares = this.boardElement.querySelectorAll('.square-55d63');

        if (squares.length === 0) {
            console.warn('No squares found - board may not be initialized yet');
            return;
        }

        console.log(`Setting up event listeners on ${squares.length} squares`);

        squares.forEach(square => {
            // Left click for circles and legal moves
            square.addEventListener('click', (e) => this.handleLeftClick(e, square));

            // Right click for arrows and removal
            square.addEventListener('contextmenu', (e) => this.handleRightClick(e, square));

            // Mouse down for arrow drag start
            square.addEventListener('mousedown', (e) => this.handleMouseDown(e, square));

            // Mouse up for arrow drag end
            square.addEventListener('mouseup', (e) => this.handleMouseUp(e, square));
        });

        // Prevent context menu on board
        this.boardElement.addEventListener('contextmenu', (e) => e.preventDefault());
    }

    /**
     * Handle left click on square (piece selection)
     */
    handleLeftClick(e, square) {
        // Legal move dots have their own click listeners, so this won't be called for them

        // If clicked on a piece image, find the parent square
        let targetSquare = square;
        if (e.target.classList.contains('piece-417db')) {
            targetSquare = e.target.parentElement;
        }

        const squareName = targetSquare.getAttribute('data-square');
        if (!squareName) {
            console.log('Click on element with no data-square attribute');
            return;
        }

        console.log('Clicked on square:', squareName);

        // Check if there's a piece on this square
        const piece = targetSquare.querySelector('.piece-417db');
        console.log('Piece found:', piece ? 'yes' : 'no');
        console.log('Chess instance:', this.chess ? 'yes' : 'no');

        if (piece && this.chess) {
            // Select piece and show legal moves
            console.log('Selecting piece and showing legal moves for', squareName);
            this.selectedSquare = squareName;
            this.showLegalMoves(squareName);
        } else {
            // Clicked on empty square - clear selection
            console.log('Empty square - clearing selection');
            this.clearSelection();
        }
    }

    /**
     * Handle right click on square (for circles and removal)
     */
    handleRightClick(e, square) {
        e.preventDefault();

        // If clicked on a piece image, find the parent square
        let targetSquare = square;
        if (e.target.classList.contains('piece-417db')) {
            targetSquare = e.target.parentElement;
        }

        const squareName = targetSquare.getAttribute('data-square');
        if (!squareName) return;

        // If not dragging, toggle circle annotation
        if (!this.isDraggingArrow) {
            // Check if there are existing annotations to remove
            const hasCircle = this.annotations.circles[squareName];
            const hasArrow = this.annotations.arrows.some(arrow => arrow.from === squareName);

            if (hasCircle || hasArrow) {
                // Remove annotations if they exist
                this.removeAnnotationsOn(squareName);
            } else {
                // Add circle annotation
                if (e.shiftKey) {
                    // Cycle through colors
                    this.addCircle(squareName, this.getNextColor());
                } else {
                    // Add circle with default color
                    this.addCircle(squareName, this.colors[0]);
                }
            }
        }
    }

    /**
     * Handle mouse down (show legal moves AND handle arrow drag start)
     */
    handleMouseDown(e, square) {
        // If clicked on a piece image, find the parent square
        let targetSquare = square;
        if (e.target.classList.contains('piece-417db')) {
            targetSquare = e.target.parentElement;
        }

        const squareName = targetSquare.getAttribute('data-square');
        if (!squareName) return;

        if (e.button === 0) { // Left mouse button - show legal moves
            // Check if there's a piece on this square
            const piece = targetSquare.querySelector('.piece-417db');

            if (piece && this.chess) {
                // Show legal moves for this piece
                console.log('Showing legal moves for', squareName);
                this.selectedSquare = squareName;
                this.showLegalMoves(squareName);
            }
            // Don't preventDefault or stopPropagation - let chessboard.js handle dragging
        } else if (e.button === 2) { // Right mouse button - arrow drag
            this.arrowDragStart = squareName;
            this.isDraggingArrow = false;
        }
    }

    /**
     * Handle mouse up (end arrow drag)
     */
    handleMouseUp(e, square) {
        if (e.button === 2 && this.arrowDragStart) { // Right mouse button
            // If clicked on a piece image, find the parent square
            let targetSquare = square;
            if (e.target.classList.contains('piece-417db')) {
                targetSquare = e.target.parentElement;
            }

            const squareName = targetSquare.getAttribute('data-square');
            if (!squareName) return;

            // If dragged to different square, draw arrow
            if (this.arrowDragStart !== squareName) {
                this.isDraggingArrow = true;
                const color = e.shiftKey ? this.getNextColor() : this.colors[0];
                this.addArrow(this.arrowDragStart, squareName, color);
            }

            this.arrowDragStart = null;
            // Reset drag flag after a small delay
            setTimeout(() => { this.isDraggingArrow = false; }, 100);
        }
    }

    /**
     * Show legal moves for a piece on the given square
     */
    showLegalMoves(square) {
        if (!this.chess) {
            console.warn('Chess.js instance not provided, cannot show legal moves');
            return;
        }

        console.log('=== LEGAL MOVES DEBUG ===');
        console.log('Square clicked:', square);
        console.log('Current FEN:', this.chess.fen());
        console.log('Current turn:', this.chess.turn(), '(w=white, b=black)');

        // Check if square has a piece
        const piece = this.chess.get(square);
        console.log('Piece on square:', piece);

        // Validate that the piece belongs to the player whose turn it is
        if (!piece) {
            console.log('No piece on this square');
            this.clearLegalMoves();
            return;
        }

        const currentTurn = this.chess.turn();
        if (piece.color !== currentTurn) {
            console.log(`Wrong turn - piece is ${piece.color} but it's ${currentTurn}'s turn`);
            this.clearLegalMoves();
            return;
        }

        // Get ALL legal moves to verify Chess.js is working
        const allMoves = this.chess.moves({ verbose: false });
        console.log('Total legal moves in position:', allMoves.length, allMoves.slice(0, 5));

        // Clear previous legal moves
        this.clearLegalMoves();

        // Get legal moves for this square
        const moves = this.chess.moves({ square: square, verbose: true });

        console.log('Legal moves for square', square + ':', moves.length);
        if (moves.length > 0) {
            console.log('Moves:', moves.map(m => m.san));
        }

        if (moves.length === 0) {
            console.log('No legal moves for this square - piece may be pinned or wrong turn');
            return;
        }

        this.legalMovesVisible = true;

        // Draw dots for each legal move
        moves.forEach(move => {
            const isCapture = move.captured || move.flags.includes('c') || move.flags.includes('e');
            this.drawLegalMoveDot(move.to, isCapture);
        });

        console.log('Legal moves displayed successfully');
        console.log('=========================');
    }

    /**
     * Draw a legal move dot on a square
     */
    drawLegalMoveDot(square, isCapture = false) {
        const coords = this.getSquareCoordinates(square);
        if (!coords) return;

        const squareSize = this.getSquareSize();
        const center = squareSize / 2;
        const radius = isCapture ? squareSize * 0.4 : squareSize * 0.15;

        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', coords.x + center);
        circle.setAttribute('cy', coords.y + center);
        circle.setAttribute('r', radius);
        circle.classList.add('legal-move-dot');
        if (isCapture) {
            circle.classList.add('legal-move-capture');
        }

        // Make dot clickable and store destination square
        circle.setAttribute('data-square', square);
        // pointer-events and cursor are now handled by CSS class

        // Add click event listener directly to the dot
        circle.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent event from reaching square below
            console.log('Legal move dot clicked:', square);
            if (this.selectedSquare && this.moveCallback) {
                console.log(`Making move: ${this.selectedSquare} → ${square}`);
                this.moveCallback(this.selectedSquare, square);
            }
        });

        this.overlay.appendChild(circle);
    }

    /**
     * Clear all legal move dots
     */
    clearLegalMoves() {
        const dots = this.overlay.querySelectorAll('.legal-move-dot');
        dots.forEach(dot => dot.remove());
        this.legalMovesVisible = false;
        this.selectedSquare = null;
    }

    /**
     * Clear selection and legal moves
     */
    clearSelection() {
        this.selectedSquare = null;
        this.clearLegalMoves();
    }

    /**
     * Toggle circle annotation on a square
     */
    toggleCircle(square) {
        if (this.annotations.circles[square]) {
            // Cycle to next color
            const currentColor = this.annotations.circles[square];
            const currentIndex = this.colors.indexOf(currentColor);
            const nextIndex = (currentIndex + 1) % this.colors.length;

            if (nextIndex === 0) {
                // Remove circle after cycling through all colors
                this.removeCircle(square);
            } else {
                this.addCircle(square, this.colors[nextIndex]);
            }
        } else {
            // Add new circle with default color
            this.addCircle(square, this.colors[0]);
        }
    }

    /**
     * Add circle annotation
     */
    addCircle(square, color) {
        this.annotations.circles[square] = color;
        this.renderAnnotations();
    }

    /**
     * Remove circle annotation
     */
    removeCircle(square) {
        delete this.annotations.circles[square];
        this.renderAnnotations();
    }

    /**
     * Add arrow annotation
     */
    addArrow(fromSquare, toSquare, color) {
        // Remove existing arrow with same from/to
        this.annotations.arrows = this.annotations.arrows.filter(
            arrow => !(arrow.from === fromSquare && arrow.to === toSquare)
        );

        // Add new arrow
        this.annotations.arrows.push({
            from: fromSquare,
            to: toSquare,
            color: color
        });

        this.renderAnnotations();
    }

    /**
     * Remove all annotations on a square
     */
    removeAnnotationsOn(square) {
        // Remove circles
        delete this.annotations.circles[square];

        // Remove arrows starting from this square
        this.annotations.arrows = this.annotations.arrows.filter(
            arrow => arrow.from !== square
        );

        this.renderAnnotations();
    }

    /**
     * Clear all annotations
     */
    clearAllAnnotations() {
        this.annotations.circles = {};
        this.annotations.arrows = [];
        this.clearLegalMoves();
        this.renderAnnotations();
    }

    /**
     * Render all annotations (circles and arrows)
     */
    renderAnnotations() {
        // Clear existing annotations (but not legal move dots)
        const circles = this.overlay.querySelectorAll('.annotation-circle');
        const arrows = this.overlay.querySelectorAll('.annotation-arrow');
        circles.forEach(c => c.remove());
        arrows.forEach(a => a.remove());

        // Render circles
        Object.entries(this.annotations.circles).forEach(([square, color]) => {
            this.drawCircle(square, color);
        });

        // Render arrows
        this.annotations.arrows.forEach(arrow => {
            this.drawArrow(arrow.from, arrow.to, arrow.color);
        });
    }

    /**
     * Draw a circle annotation
     */
    drawCircle(square, color) {
        const coords = this.getSquareCoordinates(square);
        if (!coords) return;

        const squareSize = this.getSquareSize();
        const center = squareSize / 2;
        const radius = squareSize * 0.45;

        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', coords.x + center);
        circle.setAttribute('cy', coords.y + center);
        circle.setAttribute('r', radius);
        circle.classList.add('annotation-circle', `annotation-${color}`);

        // Annotation circles should not capture clicks
        circle.style.pointerEvents = 'none';

        this.overlay.appendChild(circle);
    }

    /**
     * Draw an arrow annotation
     */
    drawArrow(fromSquare, toSquare, color) {
        const fromCoords = this.getSquareCoordinates(fromSquare);
        const toCoords = this.getSquareCoordinates(toSquare);

        if (!fromCoords || !toCoords) return;

        const squareSize = this.getSquareSize();
        const center = squareSize / 2;

        const x1 = fromCoords.x + center;
        const y1 = fromCoords.y + center;
        const x2 = toCoords.x + center;
        const y2 = toCoords.y + center;

        // Calculate arrow angle and length
        const angle = Math.atan2(y2 - y1, x2 - x1);
        const length = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);

        // Shorten arrow to not overlap pieces
        const offset = squareSize * 0.25;
        const x1adj = x1 + Math.cos(angle) * offset;
        const y1adj = y1 + Math.sin(angle) * offset;
        const x2adj = x2 - Math.cos(angle) * offset;
        const y2adj = y2 - Math.sin(angle) * offset;

        // Create arrow path
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.classList.add('annotation-arrow', `annotation-${color}`);

        // Annotation arrows should not capture clicks
        g.style.pointerEvents = 'none';

        // Arrow line
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', x1adj);
        line.setAttribute('y1', y1adj);
        line.setAttribute('x2', x2adj);
        line.setAttribute('y2', y2adj);
        line.setAttribute('marker-end', `url(#arrowhead-${color})`);

        g.appendChild(line);

        // Create arrowhead marker if it doesn't exist
        this.createArrowheadMarker(color);

        this.overlay.appendChild(g);
    }

    /**
     * Create arrowhead marker for SVG
     */
    createArrowheadMarker(color) {
        const markerId = `arrowhead-${color}`;

        // Check if marker already exists
        if (document.getElementById(markerId)) return;

        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');

        marker.setAttribute('id', markerId);
        marker.setAttribute('markerWidth', '6');
        marker.setAttribute('markerHeight', '6');
        marker.setAttribute('refX', '5');
        marker.setAttribute('refY', '3');
        marker.setAttribute('orient', 'auto');
        marker.setAttribute('markerUnits', 'strokeWidth');

        const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        polygon.setAttribute('points', '0 0, 6 3, 0 6');
        polygon.classList.add(`arrowhead-${color}`);

        marker.appendChild(polygon);
        defs.appendChild(marker);
        this.overlay.appendChild(defs);
    }

    /**
     * Get square coordinates relative to SVG overlay
     */
    getSquareCoordinates(square) {
        const squareElement = this.boardElement.querySelector(`[data-square="${square}"]`);
        if (!squareElement) return null;

        // Use SVG overlay's coordinate system for accurate positioning
        const overlayRect = this.overlay.getBoundingClientRect();
        const squareRect = squareElement.getBoundingClientRect();

        return {
            x: squareRect.left - overlayRect.left,
            y: squareRect.top - overlayRect.top
        };
    }

    /**
     * Get size of a square
     */
    getSquareSize() {
        const square = this.boardElement.querySelector('.square-55d63');
        if (!square) return 60; // Default fallback
        return square.getBoundingClientRect().width;
    }

    /**
     * Get next color in cycle
     */
    getNextColor() {
        this.currentColor = (this.currentColor + 1) % this.colors.length;
        return this.colors[this.currentColor];
    }

    /**
     * Update chess instance (for when position changes)
     */
    updateChessInstance(chessInstance) {
        this.chess = chessInstance;
    }

    /**
     * Destroy and cleanup
     */
    destroy() {
        if (this.overlay) {
            this.overlay.remove();
        }
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BoardAnnotations;
}
