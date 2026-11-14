# Backup and restore evidence

Scripts: `scripts/backup.sh` (pg_dump custom format, verified with `pg_restore --list`, keeps newest 7) and `scripts/restore.sh` (confirmation prompt, stops app, restores, waits for `/ready`).
The data here is test data, so the destructive step is safe.

Run all steps in deploy mode (`docker compose -f docker-compose.yml`) and paste the output under each heading.

## 1. Create a booking
```
$ <hold and booking commands from the runbook>
<ticket id>
$ curl -ks https://cinema.localhost/bookings/<ticket id>
<expected: "status":"CONFIRMED">
```

## 2. Back up
```
$ scripts/backup.sh
<expected: OK backups/cinema-<time>.dump (<size>)>
```

## 3. Destroy the data
```
$ docker compose -f docker-compose.yml down -v
$ docker compose -f docker-compose.yml up -d
$ until scripts/healthcheck.sh; do sleep 3; done
<paste last line>
```

## 4. Prove the booking is gone
```
$ curl -ks https://cinema.localhost/bookings/<ticket id>
<expected: {"detail":"booking not found"}>
```

## 5. Restore
```
$ scripts/restore.sh backups/<file>.dump
<paste output, ending with "restored; app ready">
```

## 6. Prove the booking is back
```
$ curl -ks https://cinema.localhost/bookings/<ticket id>
<expected: the same ticket id with "status":"CONFIRMED">
```

## Result
| Item | Value |
|---|---|
| Ticket id | `<same id in steps 1, 4 and 6>` |
| Backup file and size | `<file> / <size>` |
| Restore duration | `<seconds>` |
| Date | `<YYYY-MM-DD>` |

## Limitations
- Backups are written to the same host as the database; copy them off-host in a real deployment.
- `down -v` also removed the proxy's certificate volume, so a new local CA was generated; this does not affect data.
