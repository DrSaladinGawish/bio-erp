# IncentiveHouse ERP v5.5 - Docker Deployment

## Quick Start

```bash
# 1. Generate SSL certificates
bash scripts/gen-ssl.sh          # Linux/Mac
scripts\gen-ssl.bat              # Windows

# 2. Configure secrets
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, SECRET_KEY, JWT_SECRET

# 3. Build and run
docker-compose up --build -d

# 4. Open browser
open https://localhost           # Login: admin / admin2026
```

## Services

| Service   | Port | Description              |
|-----------|------|--------------------------|
| Nginx     | 443  | SSL reverse proxy        |
| Nginx     | 80   | HTTP → HTTPS redirect    |
| App       | 9001 | Uvicorn (internal)       |
| PostgreSQL| 5432 | Database (internal)      |
| Redis     | 6379 | Cache / Celery (internal)|

## Production SSL (Let's Encrypt)

Replace self-signed certs with real ones:

```bash
# On the server:
docker exec ih-erp-nginx apk add certbot certbot-nginx
certbot --nginx -d erp.example.com
```

Or mount certs from host:
```yaml
# In docker-compose.yml, nginx volumes:
volumes:
  - /etc/letsencrypt:/etc/letsencrypt:ro
  - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
```

## Environment Variables

All secrets go in `.env`. Required vars:

| Variable            | Description                |
|---------------------|----------------------------|
| `POSTGRES_PASSWORD` | Database password          |
| `SECRET_KEY`        | 64-char app secret         |
| `JWT_SECRET`        | 64-char JWT signing secret |

Optional but recommended:
- `IH_ADMIN_PASSWORD` — dashboard login password (default: `admin2026`)
- `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS` — email sending
- `ETA_CLIENT_ID`, `ETA_CLIENT_SECRET` — Egyptian Tax Authority

## Monitoring

```bash
# View logs
docker-compose logs -f erp
docker-compose logs -f nginx

# Health check
curl https://localhost/health

# Shell access
docker exec -it ih-erp-app /bin/bash
```
