# Operations runbook

All commands run from the repository root. `C` below means `docker compose -f docker-compose.yml`.

## 1. Deploy
```bash
cp .env.example .env            # first time only; set POSTGRES_PASSWORD and APP_VERSION
unset APP_VERSION               # a stale shell variable overrides .env
C up -d
C ps                            # db, app, proxy: healthy / running
scripts/healthcheck.sh          # health=200 ready=200
```
First start creates the `pgdata` volume and runs `db/init.sql` (schema and seed data). Later starts do not re-run it.

**New release:** wait for a green CI run on `main`, copy the 7-character tag from the job summary, then `scripts/deploy.sh <tag>`. Record it in `docs/releases.md`.

## 2. Restart
| Goal | Command |
|---|---|
| Restart one service | `C restart app` (or `db`, `proxy`) |
| Apply a Caddyfile change | `C restart proxy` |
| Apply a compose or env change | `C up -d` (recreates only what changed) |
| Stop everything, keep data | `C down` |
| Start again | `C up -d` |

Never use `down -v` on a system with data you need: it deletes the database volume.
`restart: unless-stopped` restarts crashed containers automatically, but not ones you stopped yourself.

## 3. Logs
| What | Command |
|---|---|
| App (JSON, one object per line) | `C logs app --tail 50` |
| Proxy access log (JSON) | `C logs proxy --tail 50` |
| Database | `C logs db --tail 50` |
| Follow live | `C logs -f app` |
| Errors only | `C logs app \| grep '"level": "ERROR"'` |
| Requests by status | `C logs proxy \| grep '"status":5'` |

Logs are rotated by Docker: 3 files of 10 MB per service.

## 4. Backup and restore
```bash
scripts/backup.sh                           # writes backups/cinema-<UTC time>.dump, verified, keeps newest 7
scripts/restore.sh backups/<file>.dump      # asks for 'yes', stops the app, restores, waits for /ready
```
- Run `backup.sh` before every deploy and on a schedule (for example a daily cron entry).
- After any restore, check a known record, for example `curl -ks https://cinema.localhost/bookings/<ticket_id>`.
- Backups sit on the same host. Copy them off-host for real protection.
- Evidence of a tested restore: `docs/backup-restore-evidence.md`.

## 5. Rollback
```bash
scripts/deploy.sh <previous-sha>
```
Full procedure, verification and measured time: `docs/rollback.md`.

## 6. Incident response

**Step 1: classify.** Run `scripts/healthcheck.sh`:

| health | ready | Meaning | Go to |
|---|---|---|---|
| 200 | 200 | Healthy | nothing to do |
| 200 | 503 | App up, database unreachable | Database down |
| 502 | 502 | Proxy up, app down or unhealthy | App down |
| 000 | 000 | Proxy unreachable | Proxy down |

Note: `docker compose ps` can show the app as `healthy` during a database outage, because the container health check calls `/health`. Use `/ready` (or the script) to detect it.

**Database down:** `C ps`, `C logs db --tail 30`, then `C start db`. The app reconnects by itself within 10-20 s. If the data volume is damaged, restore (section 4).

**App down:** `C logs app --tail 30`. If the logs show a bad release, roll back (section 5). Otherwise `C up -d app`.

**Proxy down:** `C logs proxy --tail 30`, `C up -d proxy`. If it will not bind, find what holds ports 80/443: `sudo ss -tlnp | grep -E ':80 |:443 '`.

**Bad release (errors after a deploy):** `scripts/deploy.sh <previous-sha>`, then verify `/ready` and `/version`.

**Data loss or corruption:** stop writes (`C stop app`), pick the newest good backup, run `scripts/restore.sh`, verify a known record.

**Step 2: record.** Note time, symptom, command output and fix in an incident log. Add new causes to `docs/troubleshooting.md`.

## 7. Routine checks
| Frequency | Check |
|---|---|
| Daily | `scripts/healthcheck.sh`; a recent file in `backups/` |
| Weekly | `docker system df` (disk); proxy log for 5xx; CI scan results |
| Per release | Backup first, deploy a SHA tag, verify `/ready`, update `docs/releases.md` |
