# Deployment Guide

## 1. Prerequisites
- Docker Engine 27+
- Docker Compose v2
- TLS certificate files at deploy/nginx/certs/fullchain.pem and deploy/nginx/certs/privkey.pem

## 2. Configure production secrets
1. Copy .env.production and set real values.
2. Rotate SECRET_KEY, MINIO credentials, and Grafana credentials.
3. Prefer *_FILE environment variables for secrets mounted from Docker secrets.

## 3. Build and start production
```bash
docker compose --env-file .env.production up -d --build
```

## 4. Validate deployment
```bash
curl -f https://localhost/api/v1/health
curl -f https://localhost/api/v1/health/readiness
curl -f https://localhost/api/v1/health/liveness
```

## 5. Development mode
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file .env.development up --build
```

## 6. Observability endpoints
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Loki API: http://localhost:3100
- MinIO console: http://localhost:9001
