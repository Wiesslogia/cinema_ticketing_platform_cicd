# Demo script (target 4:30, hard limit 5:00)

Rehearse once with a timer. Keep two terminals and one browser tab open. Record the screen at 1080p with your voice on.
Before recording: stack running in deploy mode, `scripts/healthcheck.sh` returns 200/200, a fresh backup exists, terminal font large.

| Time | Show | Say (in your own words) |
|---|---|---|
| 0:00-0:20 | README top and `docs/architecture.md` diagram | What the service is, and that the project is about build, release, deploy, observe and recover. Name the three containers. |
| 0:20-1:10 | GitHub Actions: the green run, expand the three jobs, open the job summary with tag and digest | Triggers; lint and test run in parallel; the image is built locally and **scanned before push**; push happens only on `main`; SHA tag. Briefly mention the red Trivy run you fixed. |
| 1:10-1:50 | Terminal: `docker compose -f docker-compose.yml ps`; `curl -k https://cinema.localhost/ready`; `curl -m 3 http://localhost:8000/ready` (fails); `curl -I http://cinema.localhost/ready` (redirect) | Only the proxy is published; HTTPS through Caddy; the app and database are not reachable directly; the running image is the CI one (show tag, and that the digest matches the job summary). |
| 1:50-2:20 | `pytest -v -k concurrent` | 20 simultaneous holds on one seat: exactly one 201, nineteen 409. The rule is enforced by a row lock plus a partial unique index. |
| 2:20-3:20 | **Failure drill:** terminal 2 runs `watch -n 2 scripts/healthcheck.sh`; terminal 1 runs `docker compose -f docker-compose.yml stop db`; show `ready=503` while `health=200`; show `docker compose logs app --tail 3`; `start db`; show recovery | Docker still calls the app healthy because its check uses `/health`; `/ready` catches the outage; the app reconnects without a restart. |
| 3:20-4:20 | **Restore:** show the ticket id from before; `down -v` and `up -d`; ticket returns 404; `scripts/restore.sh backups/<file>`; ticket returns 200 | Backups are verified `pg_dump` files; restore stops the app, restores and waits for `/ready`. Same ticket back. |
| 4:20-4:30 | `scripts/deploy.sh 50eddac` result or `docs/rollback.md` | Rollback is the same deploy script with an older SHA. Close with limitations: local CA, same-host backups. |

## Tips
- If a step is slow (a pull, or a restore wait), cut it in editing rather than talking over it.
- Do not show `.env`; if you must, show `.env.example`.
- Be ready to explain every command you ran, because the walkthrough will ask.
