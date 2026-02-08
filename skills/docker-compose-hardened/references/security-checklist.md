# Docker Compose Security Checklist

Use this checklist when generating or auditing compose files. Each item includes rationale and YAML syntax.

## Table of Contents

1. [Image Security](#image-security)
2. [User and Privilege](#user-and-privilege)
3. [Filesystem](#filesystem)
4. [Linux Capabilities](#linux-capabilities)
5. [Resource Limits](#resource-limits)
6. [Network Security](#network-security)
7. [Secrets and Credentials](#secrets-and-credentials)
8. [Logging and Monitoring](#logging-and-monitoring)
9. [Healthchecks](#healthchecks)
10. [Miscellaneous](#miscellaneous)

---

## Image Security

### Pin images by SHA256 digest

Tags are mutable. Pinning by digest ensures reproducible, tamper-proof builds.

```yaml
# Avoid
image: postgres:16

# Better - pin tag
image: postgres:16.4-alpine

# Best - pin digest
image: postgres@sha256:abc123...
```

To find digest: `docker pull postgres:16.4-alpine && docker inspect --format='{{index .RepoDigests 0}}' postgres:16.4-alpine`

### Use minimal base images

Prefer `-alpine`, `-slim`, or distroless variants. Smaller attack surface, fewer CVEs.

### Scan images regularly

Use `docker scout cves <image>` or Trivy to scan for known vulnerabilities.

---

## User and Privilege

### Run as non-root

```yaml
user: "65534:65534"  # nobody:nogroup
```

Some images require specific UIDs. Check image docs. Common patterns:
- PostgreSQL: `user: "999:999"`
- Redis: `user: "999:999"`
- Nginx: `user: "101:101"` (requires cap_add NET_BIND_SERVICE for port 80)

### Disable privilege escalation

```yaml
security_opt:
  - no-new-privileges:true
```

Prevents processes from gaining additional privileges via setuid/setgid binaries.

### Never use privileged mode

```yaml
# NEVER do this
privileged: true
```

Grants full access to host devices and disables all security mechanisms.

### Avoid unnecessary SYS_ADMIN

`SYS_ADMIN` is nearly equivalent to `privileged`. If a container needs it, re-evaluate the architecture.

---

## Filesystem

### Read-only root filesystem

```yaml
read_only: true
```

Prevents malware from writing to the container filesystem. Pair with tmpfs for directories that need writes:

```yaml
read_only: true
tmpfs:
  - /tmp:size=64M,noexec,nosuid,nodev
  - /run:size=64M,noexec,nosuid,nodev
  - /var/cache:size=128M,noexec,nosuid,nodev
```

### tmpfs mount options

Always apply restrictive mount options:
- `noexec` - prevent execution of binaries
- `nosuid` - ignore setuid bits
- `nodev` - no device files
- `size=NM` - limit size to prevent DoS

### Named volumes for persistent data

```yaml
volumes:
  db_data:
    driver: local

services:
  db:
    volumes:
      - db_data:/var/lib/postgresql/data
```

Avoid bind mounts to sensitive host paths. Never mount `/`, `/etc`, `/var/run/docker.sock`, or other sensitive paths.

### Never mount Docker socket

```yaml
# NEVER do this unless absolutely required (e.g., Traefik)
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

If Docker socket access is required (e.g., Traefik, Portainer), use read-only mount and consider socket proxies like Tecnativa docker-socket-proxy.

---

## Linux Capabilities

### Drop all, add back selectively

```yaml
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE  # Only if binding to ports < 1024
```

Common capabilities by need:
| Capability | When needed |
|---|---|
| `NET_BIND_SERVICE` | Binding to ports below 1024 |
| `CHOWN` | Changing file ownership at startup |
| `SETUID` / `SETGID` | Switching user at startup |
| `DAC_OVERRIDE` | Reading files not owned by container user |

If an image requires many capabilities, consider finding an alternative or building a custom image.

---

## Resource Limits

### Memory and CPU limits

```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: "1.0"
    reservations:
      memory: 128M
      cpus: "0.25"
```

Prevents resource exhaustion and container escape vectors. Set limits based on actual usage with headroom.

### PID limits

```yaml
pids_limit: 100
```

Prevents fork bombs. Adjust higher for process-heavy workloads (e.g., PHP-FPM may need 200+).

### Ulimits

```yaml
ulimits:
  nofile:
    soft: 65536
    hard: 65536
  nproc:
    soft: 4096
    hard: 4096
```

---

## Network Security

### Bind ports to localhost only

```yaml
ports:
  - "127.0.0.1:8080:8080"
```

Never use `0.0.0.0` or omit the host IP. Docker port mapping bypasses host firewall (iptables/nftables) rules.

### Use internal networks for backend services

```yaml
networks:
  backend:
    driver: bridge
    internal: true
```

`internal: true` prevents containers on this network from initiating outbound connections, limiting blast radius if compromised.

### Avoid host network mode

```yaml
# Avoid
network_mode: host
```

Host network mode bypasses all Docker network isolation.

### Disable inter-container communication when possible

```yaml
networks:
  isolated:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.enable_icc: "false"
```

### DNS configuration

```yaml
dns:
  - 1.1.1.1
  - 1.0.0.1
```

Set explicit DNS to avoid leaking internal DNS queries.

---

## Secrets and Credentials

### Use Docker secrets, not env vars

```yaml
secrets:
  db_password:
    file: ./secrets/db_password.txt

services:
  db:
    secrets:
      - db_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
```

Environment variables are visible in `docker inspect`, process listings, and logs. Secrets are mounted as files at `/run/secrets/<name>`.

### Never hardcode secrets in compose files

```yaml
# NEVER
environment:
  DB_PASSWORD: supersecret123

# If env vars are unavoidable, use .env file
env_file:
  - .env  # Make sure .env is in .gitignore and .dockerignore
```

### Secret file permissions

Secret files should be readable only by the container user. Set file permissions to `0400` or `0440`.

---

## Logging and Monitoring

### Configure log rotation

```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
```

Without limits, logs can fill disk and cause DoS.

### Avoid logging sensitive data

Configure applications to not log credentials, tokens, or PII.

---

## Healthchecks

### Add meaningful healthchecks

```yaml
healthcheck:
  test: ["CMD", "pg_isready", "-U", "postgres"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

Use service-specific checks. Avoid `curl` unless the image includes it. Use `wget -q --spider` as an alternative for Alpine images.

### Disable healthcheck inheritance when needed

```yaml
healthcheck:
  test: ["NONE"]
```

---

## Miscellaneous

### Set restart policy

```yaml
restart: unless-stopped
```

Options: `no`, `always`, `on-failure[:max-retries]`, `unless-stopped`. Use `on-failure:5` for services that should not restart indefinitely.

### Use specific compose file version

Always target the latest compose specification. Use top-level `services:` without a `version:` key (Compose V2+).

### Set stop grace period

```yaml
stop_grace_period: 10s
```

Prevents containers from hanging during shutdown.

### Set hostname explicitly

```yaml
hostname: myservice
```

Prevents information leakage from auto-generated hostnames.

### Disable default syscalls with seccomp

```yaml
security_opt:
  - no-new-privileges:true
  - seccomp:./seccomp-profile.json
```

The default Docker seccomp profile blocks ~44 of 300+ syscalls. Custom profiles can be more restrictive.

### Container labels

```yaml
labels:
  com.example.maintainer: "team@example.com"
  com.example.environment: "production"
```

Useful for management and auditing, not security per se.

### depends_on with condition

```yaml
depends_on:
  db:
    condition: service_healthy
```

Ensures services start only after dependencies are ready, preventing race conditions and crash loops.
