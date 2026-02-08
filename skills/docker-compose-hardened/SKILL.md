---
name: docker-compose-hardened
description: Generate and audit Docker Compose files with comprehensive security hardening. Use when Claude needs to (1) create new docker-compose.yml files with security best practices, (2) review or audit existing compose files for security issues, (3) harden existing compose configurations, (4) add or configure services in a compose stack. Covers runtime hardening (read-only fs, non-root, capability dropping, no-new-privileges, seccomp), network security (isolation, localhost port binding), resource limits, secrets management, image pinning, healthchecks, and logging.
---

# Docker Compose Hardened

Generate secure Docker Compose files and audit existing ones for security vulnerabilities.

## Workflow

1. **Determine the task**: generating a new compose file or auditing an existing one.
2. **For new files**: Identify required services, then apply all security defaults from the checklist.
3. **For audits**: Read the existing file, evaluate against the security checklist, report findings, and offer a hardened version.
4. **For both**: Consult service-specific patterns in `references/service-patterns.md` for any common services.

## Mandatory Security Defaults

Apply ALL of the following to every service unless explicitly incompatible:

```yaml
services:
  example:
    image: image_name@sha256:abc123  # Pin images by digest
    read_only: true                   # Read-only root filesystem
    user: "65534:65534"               # Run as non-root (nobody)
    security_opt:
      - no-new-privileges:true        # Prevent privilege escalation
    cap_drop:
      - ALL                           # Drop all Linux capabilities
    # cap_add:                        # Add back ONLY what's needed
    #   - NET_BIND_SERVICE
    tmpfs:
      - /tmp:size=64M,noexec,nosuid   # Writable temp with restrictions
      - /run:size=64M,noexec,nosuid
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
      test: ["CMD", "true"]           # Replace with real check
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
```

## Port Binding

NEVER expose ports to all interfaces. Always bind to localhost:

```yaml
# WRONG - exposed to all interfaces
ports:
  - "8080:8080"
  - "0.0.0.0:8080:8080"

# CORRECT - localhost only
ports:
  - "127.0.0.1:8080:8080"
```

If a service does not need external access (e.g., databases accessed only by other containers), do NOT use `ports:` at all. Use Docker networks for inter-container communication.

## Network Isolation

Create purpose-specific networks. Never use the default bridge:

```yaml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No external access - database/backend only

services:
  web:
    networks: [frontend, backend]
  db:
    networks: [backend]  # Only reachable by services on backend network
```

Mark backend networks as `internal: true` to prevent containers on that network from reaching the internet.

## Secrets Management

Never put secrets in environment variables or compose file directly. Use Docker secrets or mount secret files:

```yaml
secrets:
  db_password:
    file: ./secrets/db_password.txt  # File-based secret

services:
  db:
    secrets:
      - db_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
```

For services that don't support `_FILE` env vars, use an entrypoint script that reads the secret file.

## Audit Output Format

When auditing an existing compose file, report findings as:

```
## Security Audit Results

### Critical
- [issue]: [explanation + fix]

### Warning
- [issue]: [explanation + fix]

### Info
- [issue]: [explanation + fix]

### Applied Hardening
[Provide the full hardened compose file]
```

Severity levels:
- **Critical**: Privileged mode, ports on 0.0.0.0, secrets in env vars, running as root with no restrictions
- **Warning**: Missing resource limits, no healthcheck, unpinned images, missing `no-new-privileges`
- **Info**: Missing logging config, no PID limits, could use `internal: true` on networks

## References

- **Security checklist**: See [references/security-checklist.md](references/security-checklist.md) for the full hardening checklist with explanations
- **Service patterns**: See [references/service-patterns.md](references/service-patterns.md) for pre-hardened patterns for PostgreSQL, MySQL, Redis, Nginx, Traefik, Prometheus, Grafana, and more
