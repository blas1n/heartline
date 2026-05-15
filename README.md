# Heartline

Heartline is a simple, cheap, and Discord-first healthcheck service designed for indie developers and small teams. It monitors the uptime of your applications and sends alerts to Discord when services go down. Unlike complex solutions, Heartline focuses on being lightweight and easy to use, with a minimal feature set that prioritizes reliability and cost-efficiency.

## How to Use

### Create a Check

```bash
curl -X POST "http://localhost:8000/api/v1/checks" \
     -H "Content-Type: application/json" \
     -d '{"name": "My Service", "grace_seconds": 300}'
```

### Ping a Check

```bash
curl -X GET "http://localhost:8000/api/v1/checks/{id}/ping"
```

## Deploy Locally

To run Heartline locally using Docker Compose:

```bash
docker compose up
```

This will start the service on port 8000, with the database persisted in a volume.

## Environment Variables

| Variable             | Description                          |
|----------------------|--------------------------------------|
| `DISCORD_WEBHOOK_URL` | Discord webhook URL for alerts     |

## How is this different from healthchecks.io / cronitor?

| Feature              | Heartline         | healthchecks.io   | cronitor          |
|----------------------|-------------------|-------------------|-------------------|
| Cost                 | Free              | Paid plans        | Paid plans        |
| Discord Integration  | First-class       | Limited           | No                |
| Simplicity           | Minimal, focused  | Feature-rich      | Feature-rich      |
| Deployment           | Self-hosted       | Cloud-hosted      | Cloud-hosted      |
