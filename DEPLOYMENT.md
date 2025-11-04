# Chess Platform - Production Deployment Guide

## Prerequisites

- Hetzner bare metal server (Ubuntu 22.04 or later recommended)
- Domain `chess.snacceroni.com` pointing to your server's IP address
- SSH access to the server
- Docker and Docker Compose installed on the server

## Step 1: Server Setup

### 1.1 Connect to your Hetzner server

```bash
ssh root@YOUR_SERVER_IP
```

### 1.2 Update system packages

```bash
apt update && apt upgrade -y
```

### 1.3 Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version
```

### 1.4 Install Git

```bash
apt install git -y
```

### 1.5 Configure firewall

```bash
# Install UFW if not already installed
apt install ufw -y

# Allow SSH, HTTP, and HTTPS
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# Enable firewall
ufw enable
ufw status
```

## Step 2: Clone Repository

```bash
# Create app directory
mkdir -p /opt/apps
cd /opt/apps

# Clone repository
git clone https://github.com/YassineElZaart/learn-chess.git
cd learn-chess
```

## Step 3: Configure Environment

### 3.1 Create .env file

```bash
cp .env.example .env
nano .env
```

### 3.2 Update the .env file with secure values:

```env
# IMPORTANT: Change all these values!

# Django Settings
DEBUG=False
SECRET_KEY=GENERATE_A_LONG_RANDOM_SECRET_KEY_HERE
ALLOWED_HOSTS=chess.snacceroni.com,www.chess.snacceroni.com

# Database
POSTGRES_DB=chess_platform
POSTGRES_USER=chess_user
POSTGRES_PASSWORD=USE_A_STRONG_PASSWORD_HERE
DATABASE_URL=postgres://chess_user:USE_A_STRONG_PASSWORD_HERE@db:5432/chess_platform

# Redis
REDIS_URL=redis://redis:6379/0

# Email (optional - for production notifications)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password

# Security
CSRF_TRUSTED_ORIGINS=https://chess.snacceroni.com,https://www.chess.snacceroni.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

**To generate a secure SECRET_KEY**, run:

```bash
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

## Step 4: SSL Certificate Setup (Let's Encrypt)

### 4.1 Initial setup without SSL

First, temporarily modify the nginx configuration to work without SSL:

```bash
# Backup the original config
cp nginx/conf.d/chess.conf nginx/conf.d/chess.conf.backup

# Create a temporary HTTP-only config
cat > nginx/conf.d/chess.conf << 'EOF'
upstream django {
    server web:8000;
}

server {
    listen 80;
    server_name chess.snacceroni.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location /static/ {
        alias /app/staticfiles/;
    }

    location /media/ {
        alias /app/media/;
    }

    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
```

### 4.2 Start services

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 4.3 Obtain SSL certificate

```bash
docker compose -f docker-compose.prod.yml run --rm certbot certonly --webroot \
  --webroot-path /var/www/certbot \
  -d chess.snacceroni.com \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email
```

### 4.4 Restore full nginx configuration

```bash
cp nginx/conf.d/chess.conf.backup nginx/conf.d/chess.conf
```

### 4.5 Restart nginx

```bash
docker compose -f docker-compose.prod.yml restart nginx
```

## Step 5: Initialize Database

```bash
# Run migrations
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# Create superuser
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# Collect static files (if not done automatically)
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

## Step 6: Verify Deployment

### 6.1 Check services status

```bash
docker compose -f docker-compose.prod.yml ps
```

All services should show "Up" status.

### 6.2 Check logs

```bash
# View all logs
docker compose -f docker-compose.prod.yml logs

# View specific service logs
docker compose -f docker-compose.prod.yml logs web
docker compose -f docker-compose.prod.yml logs nginx
docker compose -f docker-compose.prod.yml logs db
```

### 6.3 Test the website

Open your browser and navigate to:
- https://chess.snacceroni.com

You should see the chess platform running with a valid SSL certificate!

## Step 7: Maintenance Commands

### Update application

```bash
cd /opt/apps/learn-chess

# Pull latest changes
git pull origin main

# Rebuild and restart services
docker compose -f docker-compose.prod.yml up -d --build

# Run migrations
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# Collect static files
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### View logs

```bash
# Follow all logs
docker compose -f docker-compose.prod.yml logs -f

# Follow specific service
docker compose -f docker-compose.prod.yml logs -f web
```

### Restart services

```bash
# Restart all services
docker compose -f docker-compose.prod.yml restart

# Restart specific service
docker compose -f docker-compose.prod.yml restart web
```

### Stop services

```bash
docker compose -f docker-compose.prod.yml down
```

### Backup database

```bash
# Create backup
docker compose -f docker-compose.prod.yml exec db pg_dump -U chess_user chess_platform > backup_$(date +%Y%m%d_%H%M%S).sql

# To restore
cat backup_XXXXXXXX_XXXXXX.sql | docker compose -f docker-compose.prod.yml exec -T db psql -U chess_user chess_platform
```

## Troubleshooting

### SSL Certificate issues

If SSL certificate isn't working:

```bash
# Check certbot logs
docker compose -f docker-compose.prod.yml logs certbot

# Try obtaining certificate again
docker compose -f docker-compose.prod.yml run --rm certbot certonly --webroot \
  --webroot-path /var/www/certbot \
  -d chess.snacceroni.com \
  --email your-email@example.com \
  --agree-tos \
  --force-renewal
```

### Database connection issues

```bash
# Check database status
docker compose -f docker-compose.prod.yml exec db pg_isready -U chess_user

# Connect to database
docker compose -f docker-compose.prod.yml exec db psql -U chess_user -d chess_platform
```

### Container not starting

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs web

# Rebuild from scratch
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d --build
```

## Security Checklist

- [ ] Changed all default passwords in .env
- [ ] Generated strong SECRET_KEY
- [ ] Set DEBUG=False
- [ ] Configured proper ALLOWED_HOSTS
- [ ] SSL certificate obtained and working
- [ ] Firewall (UFW) enabled
- [ ] Regular backups scheduled
- [ ] Monitoring setup (optional but recommended)

## Monitoring (Optional)

For production monitoring, consider:

1. **Logs aggregation**: Set up centralized logging
2. **Uptime monitoring**: Use services like UptimeRobot or Pingdom
3. **Resource monitoring**: Install htop, netdata, or similar tools
4. **Backup automation**: Set up cron jobs for regular database backups

## Support

For issues or questions:
- GitHub Issues: https://github.com/YassineElZaart/learn-chess/issues
- Check Django logs: `docker compose -f docker-compose.prod.yml logs web`
