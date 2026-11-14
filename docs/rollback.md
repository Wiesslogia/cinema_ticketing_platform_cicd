# Rollback procedure

## Roll back an image, or restore data?

| Situation | Action | Data touched? | Typical time |
|---|---|---|---|
| A new release misbehaves (errors, wrong behaviour) but data is intact | **Roll back the image** (this document) | No | under 1 minute |
| Data is lost or corrupted | **Restore a backup** (`scripts/restore.sh`, see `docs/backup-restore-evidence.md`) | Yes, overwrites | a few minutes |

This service has no database migrations, so an image rollback never has to undo a schema change. If migrations are added later, this procedure needs a separate step for them.

## How a release is identified
- Every image pushed by CI on `main` is tagged with the 7-character commit SHA, e.g. `ghcr.io/wiesslogia/cinema-api:50eddac`.
- Images are only pushed after lint, tests and the Trivy scan pass.
- Deployment never uses `latest`. The running version is `APP_VERSION` in `.env`.
- Past releases are listed in `docs/releases.md` (tag, digest, status).

## Roll back (one command)
```
unset APP_VERSION                       # a stale shell variable would override .env
scripts/deploy.sh <previous-sha>
```
Example: `scripts/deploy.sh 50eddac`

What the script does:
1. Rejects anything that is not a 7-character SHA.
2. Remembers the current `APP_VERSION`, then writes the new one to `.env`.
3. Pulls the image. If the pull fails, `.env` is restored and nothing changes.
4. Recreates only the `app` container.
5. Waits up to 60 s for `/ready` to return 200, and exits non-zero if it does not.
6. Prints the running image and its digest.

## Find the previous tag
1. `docs/releases.md`, the row marked `previous good`.
2. Or the repository's Packages page on GitHub (all pushed tags).
3. Or `git log --oneline` and take the 7-character SHA of an earlier commit that has a green CI run on `main`.

## Verify the rollback worked
```
docker compose -f docker-compose.yml ps app
curl -ks https://cinema.localhost/ready
curl -ks -o /dev/null -w '%{http_code}\n' https://cinema.localhost/version
scripts/healthcheck.sh
```
- `ps` shows `ghcr.io/wiesslogia/cinema-api:<previous-sha>`.
- `/ready` returns `{"status":"ready"}`.
- `/version` returns **404** when rolling back to `50eddac` (that release predates the endpoint). Rolling back to any later release returns its own SHA.
- The digest printed by the script matches the digest recorded in `docs/releases.md`.

## Measured drill
| Item | Value |
|---|---|
| Date of drill | <YYYY-MM-DD> |
| From | <v2-sha> |
| To | 50eddac |
| Rollback duration (`time scripts/deploy.sh 50eddac`) | <seconds> s |
| `/version` after rollback | 404 |
| Digest after rollback | sha256:7f7660396c4ec67d690d1f6106b0c484e28e3a08f8e39e19bf292f40feedf53e |

## If the rollback itself fails
| Symptom | Fix |
|---|---|
| `usage:` message | Tag is not exactly 7 hex characters |
| Pull fails with `unauthorized` or `not found` | Package is private, or that tag was never pushed (see `docs/troubleshooting.md`, rows 6) |
| `NOT READY after deploying` | `docker compose -f docker-compose.yml logs app --tail 30`; check `db` is healthy; try the next older tag |
| Script uses the wrong version | A stale `APP_VERSION` is exported in the shell: `unset APP_VERSION` |
