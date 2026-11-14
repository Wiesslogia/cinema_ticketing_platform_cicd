# Evidence index

Fill every `<...>` before submitting. Keep raw output (copy from the terminal) rather than summaries.

## 1. CI/CD
| Item | Value |
|---|---|
| Pipeline workflow | `.github/workflows/ci.yaml` |
| Green run (lint, test, build, scan, push) | `<run URL>` |
| Red run (Trivy blocked HIGH findings before push) | `<run URL>` |
| Date of both | `<YYYY-MM-DD>` |

What the red run shows: the scan found 5 HIGH findings (3 in starlette, 2 in zlib1g) and the job failed **before** any push. The fix upgraded `fastapi`/`starlette` in `requirements.txt` and patched the base layer; the later run is green.

Trivy result in the green run (paste the summary lines):
```
<Total: 0 (HIGH: 0, CRITICAL: 0) lines>
```

## 2. Image tag and digest
| Item | Value |
|---|---|
| Registry image | `ghcr.io/wiesslogia/cinema-api` |
| Deployed tag | `50eddac` |
| Digest (running on the host, `docker image inspect`) | `sha256:7f7660396c4ec67d690d1f6106b0c484e28e3a08f8e39e19bf292f40feedf53e` |
| Digest in the CI job summary for that commit | `<paste, and confirm it matches the line above>` |
| Latest release tag / digest | `<v2-sha>` / `sha256:<digest>` |

## 3. Deployment and health
Deploy mode output (`docker compose -f docker-compose.yml ps`):
```
cinema_ticketing_platform_cicd-app-1     ghcr.io/wiesslogia/cinema-api:50eddac   Up (healthy)   8000/tcp
cinema_ticketing_platform_cicd-db-1      postgres:16-alpine                      Up (healthy)   5432/tcp
cinema_ticketing_platform_cicd-proxy-1   caddy:2                                 Up             0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
```
```
$ curl -k https://cinema.localhost/ready
{"status":"ready"}
$ curl -m 3 http://localhost:8000/ready
curl: (7) Failed to connect to localhost port 8000 ... Could not connect to server
$ curl -I http://cinema.localhost/ready
HTTP/1.1 308 Permanent Redirect
Location: https://cinema.localhost/ready
```
Meaning: only the proxy is published; the app is not reachable directly; HTTP redirects to HTTPS; the running image is the CI-built, SHA-tagged one.

Response headers (`curl -kI https://cinema.localhost/ready`): `Strict-Transport-Security` and `X-Content-Type-Options` present, no `Server` header.

Log rotation (`docker inspect --format '{{.Name}} {{.HostConfig.LogConfig}}' ...`):
```
/cinema_ticketing_platform_cicd-app-1 {json-file map[max-file:3 max-size:10m]}
/cinema_ticketing_platform_cicd-db-1 {json-file map[max-file:3 max-size:10m]}
/cinema_ticketing_platform_cicd-proxy-1 {json-file map[max-file:3 max-size:10m]}
```

## 4. Domain rule tests
Command: `pytest -v` (dev mode). Result: **6 passed**.
```
tests/test_api.py::test_health_and_ready PASSED
tests/test_api.py::test_seed_data PASSED
tests/test_api.py::test_full_flow_and_cancel PASSED
tests/test_api.py::test_concurrent_holds_only_one_wins PASSED
tests/test_api.py::test_concurrent_confirm_same_hold_only_one_booking PASSED
tests/test_api.py::test_expired_hold_cannot_confirm_and_seat_reopens PASSED
```
`test_concurrent_holds_only_one_wins` sends 20 simultaneous holds for one seat: exactly 1 returns 201 and 19 return 409. `test_concurrent_confirm_same_hold_only_one_booking` sends 10 simultaneous confirms of one hold: exactly 1 booking is created.

Experiment: removing `FOR UPDATE` from `lock_seat()`:
```
<which tests failed and the status codes you saw, then confirm 6 passed after restoring it>
```

## 5. Failure and recovery, backup and restore, rollback
- Failure drills: [drills.md](drills.md)
- Backup and restore: [backup-restore-evidence.md](backup-restore-evidence.md)
- Rollback: [rollback.md](rollback.md) and [releases.md](releases.md)

## 6. Clean-environment test
| Item | Value |
|---|---|
| Fresh clone location | `<path>` |
| Steps followed | README "Quick start" only |
| Result | `<ready=200 after N minutes; any step that was unclear>` |
