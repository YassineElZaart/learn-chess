# Chess Teaching Platform

A complete Django-based chess teaching platform with interactive lessons, real-time gameplay, and a board editor.

## Features

### 📚 Interactive Lessons System
- Structured curriculum organized by difficulty levels (Beginner, Intermediate, Advanced)
- Topics with multiple practice positions
- Move sequences with detailed explanations
- Progress tracking across all lessons
- Mark positions as completed

### 🛠️ Board Editor
- Interactive chessboard with drag-and-drop piece placement
- Piece toolbar for adding/removing pieces
- Turn toggle (White/Black to move)
- FEN string display and validation
- Generate shareable game links from any position
- Save positions to lessons (admin only)

### ⚡ Real-Time Gameplay
- WebSocket-based live games using Django Channels
- Move validation with python-chess
- Play from any custom position
- Resign and draw offer functionality
- Move history with PGN notation
- Automatic reconnection handling

### 👤 User Management
- User registration and authentication
- User profiles with game history
- Progress tracking dashboard
- Game statistics

### 🎯 Admin Panel
- Full CRUD operations for lessons, topics, and positions
- Inline editing for positions within topics
- FEN validator
- Bulk operations
- Game management

## Technology Stack

- **Backend**: Django 5.0+
- **Database**: PostgreSQL 16
- **Cache/Channels**: Redis 7
- **WebSockets**: Django Channels with channels-redis
- **Chess Engine**: python-chess
- **Frontend**: Chessboard.js, Tailwind CSS, HTMX
- **Containerization**: Docker & Docker Compose

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git

## Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd learnchess
```

### 2. Environment Configuration

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and update the following:

```env
DEBUG=True
SECRET_KEY=your-secret-key-here-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_URL=postgres://chess_user:chess_password@localhost:5432/chess_platform
REDIS_URL=redis://localhost:6379/0
```

### 3. Start Services with Docker

```bash
# Start PostgreSQL and Redis
docker-compose up -d db redis

# Wait for services to be healthy
docker-compose ps
```

### 4. Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Run Migrations

```bash
python manage.py migrate
```

### 6. Create Superuser

```bash
python manage.py createsuperuser
```

### 7. Seed Initial Lessons

```bash
python manage.py seed_lessons
```

This will create 3 initial lessons:
1. Basic Checkmates (Back Rank Mate, Queen and King Mate)
2. Tactical Patterns (Forks, Pins, Skewers)
3. Opening Principles (Control Center, Develop Pieces, Castle Early)

### 8. Collect Static Files (Production)

```bash
python manage.py collectstatic --noinput
```

### 9. Run the Development Server

```bash
# For WebSocket support, use Daphne
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# Or for HTTP only during development
python manage.py runserver
```

Visit `http://localhost:8000` to access the platform.

## Using Docker (Alternative Full Stack)

To run the entire application with Docker:

```bash
# Build and start all services
docker-compose up --build

# In another terminal, run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Seed lessons
docker-compose exec web python manage.py seed_lessons
```

Access at `http://localhost:8000`

## Project Structure

```
learnchess/
├── config/                 # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── core/                   # Core models and admin
│   ├── models.py          # All database models
│   ├── admin.py           # Admin configuration
│   ├── chess_engine.py    # python-chess wrapper
│   └── management/
│       └── commands/
│           └── seed_lessons.py
├── board_editor/          # Board editor app
│   ├── views.py
│   ├── urls.py
│   └── templates/
├── lessons/               # Lessons app
│   ├── views.py
│   ├── urls.py
│   └── templates/
├── gameplay/              # Live gameplay app
│   ├── consumers.py       # WebSocket consumer
│   ├── routing.py         # WebSocket routing
│   ├── views.py
│   └── templates/
├── accounts/              # User authentication
│   ├── views.py
│   └── templates/
├── static/                # Static files
│   ├── js/
│   │   ├── board_editor.js
│   │   ├── game.js
│   │   └── position_viewer.js
│   └── css/
│       └── custom.css
├── templates/             # Base templates
│   ├── base.html
│   └── home.html
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── manage.py
└── README.md
```

## Usage Guide

### For Students

1. **Register/Login**: Create an account or log in
2. **Browse Lessons**: View available lessons organized by difficulty
3. **Study Positions**: Click through positions with explanations
4. **Practice**: Generate practice games from any position
5. **Track Progress**: Mark positions as complete and view your progress

### For Teachers/Admins

1. **Access Admin Panel**: Navigate to `/admin/`
2. **Create Lessons**: Add new lessons with topics
3. **Add Positions**: Add chess positions with FEN strings
4. **Create Sequences**: Add move sequences with explanations
5. **Monitor Progress**: View student progress and game history

### Using the Board Editor

1. Navigate to `/editor/`
2. Use drag-and-drop to arrange pieces
3. Click "Add Pieces" buttons to place pieces
4. Toggle turn (White/Black to move)
5. Copy FEN or generate a game link
6. (Admin) Save position to a lesson

### Playing Live Games

1. **Create Game**: Use board editor to generate a link
2. **Share Link**: Send the unique URL to opponent
3. **Join Game**: Opponent clicks link and joins as White/Black
4. **Play**: Make moves by dragging pieces
5. **Game Controls**: Use resign/draw buttons as needed

## Database Models

### Core Models

- **Lesson**: Top-level lesson container
- **Topic**: Topics within lessons
- **Position**: Chess positions with FEN strings
- **PositionSequence**: Move sequences for positions
- **Game**: Live game sessions
- **GameMove**: Individual moves in games
- **UserProgress**: User completion tracking

## API Endpoints

### Board Editor
- `GET /editor/` - Board editor interface
- `POST /editor/validate-fen/` - Validate FEN string
- `POST /editor/generate-game-link/` - Create game from position
- `POST /editor/save-position/` - Save position to lesson (admin)

### Lessons
- `GET /lessons/` - List all lessons
- `GET /lessons/<id>/` - Lesson detail
- `GET /lessons/topic/<id>/` - Topic detail
- `GET /lessons/position/<id>/` - Position viewer
- `POST /lessons/position/<id>/complete/` - Mark position complete
- `POST /lessons/position/<id>/practice/` - Create practice game

### Gameplay
- `GET /game/<uuid>/` - Live game interface
- `WS /ws/game/<uuid>/` - WebSocket connection
- `GET /game/` - User's game list

### Accounts
- `GET /accounts/login/` - Login page
- `GET /accounts/register/` - Registration page
- `GET /accounts/profile/` - User profile

## WebSocket Protocol

### Client -> Server Messages

```json
// Make a move
{
  "type": "make_move",
  "move": "e2e4"
}

// Join game
{
  "type": "join_game",
  "color": "white"
}

// Resign
{
  "type": "resign"
}

// Offer draw
{
  "type": "offer_draw"
}

// Accept draw
{
  "type": "accept_draw"
}
```

### Server -> Client Messages

```json
// Game state update
{
  "type": "game_state",
  "data": {
    "fen": "...",
    "status": "in_progress",
    "current_turn": "white",
    "white_player": "username",
    "black_player": "username"
  }
}

// Move made
{
  "type": "move_made",
  "move": "e2e4",
  "data": { /* game state */ }
}

// Error
{
  "type": "error",
  "message": "Invalid move"
}
```

## Development

### Running Tests

```bash
python manage.py test
```

### Code Quality

```bash
# Check for issues
python manage.py check

# Validate migrations
python manage.py makemigrations --check --dry-run
```

### Adding New Lessons

Use the Django admin panel or create a custom management command:

```python
# core/management/commands/my_lessons.py
from django.core.management.base import BaseCommand
from core.models import Lesson, Topic, Position

class Command(BaseCommand):
    help = 'Add custom lessons'

    def handle(self, *args, **options):
        # Create your lessons here
        pass
```

## Production Deployment

### Security Checklist

1. Set `DEBUG=False` in production
2. Generate strong `SECRET_KEY`
3. Configure `ALLOWED_HOSTS`
4. Enable HTTPS (uncomment security settings in settings.py)
5. Use environment variables for sensitive data
6. Set up proper database backups
7. Configure email backend for user notifications

### Environment Variables

```env
DEBUG=False
SECRET_KEY=<strong-secret-key>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

DATABASE_URL=postgres://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### Deployment with Gunicorn & Daphne

```bash
# Install production dependencies
pip install gunicorn daphne

# Run Daphne for ASGI (WebSockets)
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# Or use Gunicorn for HTTP only
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### Nginx Configuration Example

```nginx
upstream django {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://django;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /static/ {
        alias /path/to/staticfiles/;
    }
}
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps

# View logs
docker-compose logs db
```

### Redis Connection Issues

```bash
# Test Redis connection
docker-compose exec redis redis-cli ping
```

### WebSocket Not Connecting

1. Ensure Daphne is running (not runserver)
2. Check CHANNEL_LAYERS configuration in settings.py
3. Verify Redis is accessible
4. Check browser console for errors

### Static Files Not Loading

```bash
# Collect static files
python manage.py collectstatic --noinput

# Check STATIC_ROOT and STATIC_URL in settings
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review Django and Channels documentation

## Acknowledgments

- python-chess for chess logic
- Chessboard.js for the interactive board
- Django Channels for WebSocket support
- Tailwind CSS for styling
