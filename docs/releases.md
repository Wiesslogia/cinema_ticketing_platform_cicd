# Releases

One row per image deployed. Tags are commit SHAs. Digests are the content hash of the image, from the CI job summary and confirmed with
`docker image inspect --format '{{index .RepoDigests 0}}' ghcr.io/wiesslogia/cinema-api:<tag>`.

| Tag | First deployed | Digest | CI run | Status | Notes |
|---|---|---|---|---|---|
| 50eddac | 2026-11-13 | sha256:7f7660396c4ec67d690d1f6106b0c484e28e3a08f8e39e19bf292f40feedf53e | <run URL> | previous good | Patched starlette/fastapi; Trivy clean; first image deployed from GHCR |
| <v2-sha> | <YYYY-MM-DD> | sha256:<digest from job summary> | <run URL> | current | Adds `GET /version` |

## Status values
- `current`: running now
- `previous good`: tested, safe rollback target
- `retired`: superseded, do not roll back to it
- `bad`: known problem, never redeploy (add the reason under Notes)

## Update procedure
After every deploy or rollback: set the running release to `current`, set the one before it to `previous good`, and fill in its digest from the script's output.
