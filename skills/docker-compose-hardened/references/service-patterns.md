# Hardened Service Patterns

Pre-hardened Docker Compose configurations for common services. Copy and adapt these patterns when generating compose files.

## Table of Contents

1. [PostgreSQL](#postgresql)
2. [MySQL / MariaDB](#mysql--mariadb)
3. [Redis](#redis)
4. [Nginx (Reverse Proxy)](#nginx-reverse-proxy)
5. [Traefik](#traefik)
6. [Node.js / Python Web App](#nodejs--python-web-app)
7. [Prometheus](#prometheus)
8. [Grafana](#grafana)
9. [Adminer / pgAdmin](#adminer--pgadmin)

---

## PostgreSQL

```yaml
services:
  postgres:
    image: postgres:16.4-alpine  # Pin to digest in production
    read_only: true
    user: "70:70"  # postgres user in Alpine
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:size=64M,noexec,nosuid,nodev
      - /run/postgresql:size=16M,noexec,nosuid,nodev
    volumes:
      - postgres_data:/var/lib/postgresql/data
    secrets:
      - db_password
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    networks:
      - backend
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "2.0"
    pids_limit: 100
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d appdb"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
```

Notes:
- No `ports:` — only accessible via backend network
- Alpine variant uses UID 70 for postgres user
- `POSTGRES_PASSWORD_FILE` reads secret from mounted file
- tmpfs on `/run/postgresql` for Unix socket

---

## MySQL / MariaDB

```yaml
services:
  mysql:
    image: mysql:8.4-oracle  # Pin to digest in production
    read_only: true
    user: "999:999"  # mysql user
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:size=64M,noexec,nosuid,nodev
      - /run/mysqld:size=16M,noexec,nosuid,nodev
    volumes:
      - mysql_data:/var/lib/mysql
    secrets:
      - db_root_password
      - db_password
    environment:
      MYSQL_DATABASE: appdb
      MYSQL_USER: appuser
      MYSQL_ROOT_PASSWORD_FILE: /run/secrets/db_root_password
      MYSQL_PASSWORD_FILE: /run/secrets/db_password
    networks:
      - backend
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "2.0"
    pids_limit: 200
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "appuser", "--password-from-stdin"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

Notes:
- Higher PID limit (200) — MySQL uses more threads
- Longer start_period for initial database creation

---

## Redis

```yaml
services:
  redis:
    image: redis:7-alpine  # Pin to digest in production
    read_only: true
    user: "999:999"
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:size=32M,noexec,nosuid,nodev
    volumes:
      - redis_data:/data
    command: >
      redis-server
      --requirepass-file /run/secrets/redis_password
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
      --rename-command FLUSHALL ""
      --rename-command FLUSHDB ""
      --rename-command DEBUG ""
      --rename-command CONFIG ""
    secrets:
      - redis_password
    networks:
      - backend
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
    pids_limit: 50
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
```

Notes:
- Dangerous commands renamed to empty string (disabled)
- `maxmemory` set with eviction policy
- No ports exposed — backend network only
- If Redis version doesn't support `--requirepass-file`, use entrypoint script to read secret

---

## Nginx (Reverse Proxy)

```yaml
services:
  nginx:
    image: nginx:1.27-alpine  # Pin to digest in production
    read_only: true
    user: "101:101"  # nginx user in Alpine
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Required for port 80/443
    tmpfs:
      - /tmp:size=64M,noexec,nosuid,nodev
      - /var/cache/nginx:size=128M,noexec,nosuid,nodev
      - /run:size=16M,noexec,nosuid,nodev
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
    ports:
      - "127.0.0.1:80:80"
      - "127.0.0.1:443:443"
    networks:
      - frontend
      - backend
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "1.0"
    pids_limit: 100
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost/health || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    depends_on:
      app:
        condition: service_healthy
```

Notes:
- Config mounted read-only (`:ro`)
- `NET_BIND_SERVICE` needed for ports < 1024. Alternative: listen on 8080 and drop this cap
- tmpfs for Nginx cache, run, tmp directories
- On both frontend and backend networks to proxy requests

---

## Traefik

```yaml
services:
  traefik:
    image: traefik:3.1  # Pin to digest in production
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    tmpfs:
      - /tmp:size=32M,noexec,nosuid,nodev
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro  # Required, use socket proxy in production
      - ./traefik/traefik.yml:/etc/traefik/traefik.yml:ro
      - traefik_certs:/etc/traefik/acme
    ports:
      - "127.0.0.1:80:80"
      - "127.0.0.1:443:443"
    networks:
      - frontend
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.5"
    pids_limit: 50
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD", "traefik", "healthcheck"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s
    labels:
      - "traefik.enable=false"  # Don't expose Traefik's own dashboard by default
```

Notes:
- Docker socket mounted read-only — **strongly recommend** using a Docker socket proxy (e.g., `tecnativa/docker-socket-proxy`) instead of direct mount
- Dashboard disabled by default via label
- Traefik does not easily run as non-root; mitigate with all other hardening measures

Docker socket proxy pattern:
```yaml
  socket-proxy:
    image: tecnativa/docker-socket-proxy
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    environment:
      CONTAINERS: 1
      SERVICES: 0
      TASKS: 0
      NETWORKS: 0
      VOLUMES: 0
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - socket-proxy
    deploy:
      resources:
        limits:
          memory: 64M
          cpus: "0.25"
    pids_limit: 50
    restart: unless-stopped

  traefik:
    # ... same as above but replace socket mount with:
    environment:
      DOCKER_HOST: tcp://socket-proxy:2375
    networks:
      - frontend
      - socket-proxy
    # Remove the docker.sock volume mount
```

---

## Node.js / Python Web App

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    read_only: true
    user: "1000:1000"  # Match Dockerfile non-root user
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:size=64M,noexec,nosuid,nodev
    environment:
      NODE_ENV: production  # Or FLASK_ENV, etc.
    secrets:
      - app_secret_key
      - db_connection_string
    networks:
      - backend
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
    pids_limit: 100
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:3000/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
```

Notes:
- No ports exposed — accessed through reverse proxy
- Build from local Dockerfile (ensure Dockerfile uses non-root USER)
- Secrets for sensitive config, env vars for non-sensitive config only

---

## Prometheus

```yaml
services:
  prometheus:
    image: prom/prometheus:v2.54.0  # Pin to digest in production
    read_only: true
    user: "65534:65534"  # nobody
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--storage.tsdb.retention.time=30d"
      - "--web.console.libraries=/etc/prometheus/console_libraries"
      - "--web.console.templates=/etc/prometheus/consoles"
      - "--web.enable-lifecycle"
    networks:
      - monitoring
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "1.0"
    pids_limit: 100
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:9090/-/healthy || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s
```

---

## Grafana

```yaml
services:
  grafana:
    image: grafana/grafana:11.1.0  # Pin to digest in production
    read_only: true
    user: "472:472"  # grafana user
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:size=64M,noexec,nosuid,nodev
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
    secrets:
      - grafana_admin_password
    environment:
      GF_SECURITY_ADMIN_PASSWORD__FILE: /run/secrets/grafana_admin_password
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_SECURITY_DISABLE_GRAVATAR: "true"
      GF_ANALYTICS_REPORTING_ENABLED: "false"
    ports:
      - "127.0.0.1:3000:3000"
    networks:
      - monitoring
      - frontend
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
    pids_limit: 100
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:3000/api/health || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
```

Notes:
- Grafana signup disabled, Gravatar disabled (privacy), analytics reporting off
- Uses `__FILE` suffix for secret injection

---

## Adminer / pgAdmin

```yaml
services:
  adminer:
    image: adminer:4  # Pin to digest in production
    read_only: true
    user: "1000:1000"
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:size=32M,noexec,nosuid,nodev
    ports:
      - "127.0.0.1:8080:8080"
    networks:
      - backend
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: "0.5"
    pids_limit: 50
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:8080 || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
```

Notes:
- Database admin tools should ONLY be accessible on localhost
- Consider removing from production compose files entirely — use only in dev/staging
- For pgAdmin, use similar pattern with `dpage/pgadmin4` image and UID `5050:5050`

---

## Full Stack Example

Complete example combining web app + PostgreSQL + Redis + Nginx:

```yaml
secrets:
  db_password:
    file: ./secrets/db_password.txt
  redis_password:
    file: ./secrets/redis_password.txt
  app_secret:
    file: ./secrets/app_secret.txt

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true

volumes:
  postgres_data:
  redis_data:

services:
  nginx:
    # See Nginx pattern above
    depends_on:
      app:
        condition: service_healthy

  app:
    # See Web App pattern above
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  postgres:
    # See PostgreSQL pattern above

  redis:
    # See Redis pattern above
```
