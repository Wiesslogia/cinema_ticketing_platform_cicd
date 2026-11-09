# Cinema Show & Seat Reservation API

## Run
    cp .env.example .env        # then edit the password
    docker compose up -d --build
    curl localhost:8000/ready

## Test (needs the db container up)
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements-dev.txt
    export DATABASE_URL=postgresql://cinema:change-me@127.0.0.1:5432/cinema
    pytest -v

## API
| Method | Path | Purpose |
|---|---|---|
| GET | /health, /ready | liveness, readiness |
| GET | /shows | list shows |
| GET | /shows/{id}/seats | seat map (AVAILABLE/HELD/BOOKED) |
| POST | /shows/{id}/holds `{"seat":"A1"}` | hold a seat (TTL) |
| POST | /bookings `{"show_id":1,"seat":"A1","hold_token":"..."}` | confirm, returns ticket_id |
| POST | /bookings/{ticket_id}/cancel | cancel |
