import json
import logging
import os
import secrets
import threading
import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from psycopg import errors
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel


# ---------- structured (JSON) logging ----------
class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        return json.dumps(payload)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
log = logging.getLogger("cinema")
log.setLevel(logging.INFO)
log.addHandler(handler)
log.propagate = False


# ---------- database pool (lazy, so tests/containers start cleanly) ----------
_pool = None
_pool_lock = threading.Lock()


def get_pool() -> ConnectionPool:
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = ConnectionPool(
                os.environ["DATABASE_URL"],
                min_size=1,
                max_size=10,
                kwargs={"row_factory": dict_row},
                open=True,
            )
        return _pool


def hold_ttl() -> int:
    return int(os.environ.get("HOLD_TTL_SECONDS", "300"))


app = FastAPI(title="Cinema Show & Seat Reservation API")


@app.middleware("http")
async def access_log(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    log.info(
        "request",
        extra={
            "fields": {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "ms": round((time.perf_counter() - start) * 1000, 1),
            }
        },
    )
    return response


# ---------- health ----------
@app.get("/health")
def health():
    """Liveness: the process is up. Does not touch the database."""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """Readiness: the database is reachable."""
    try:
        with get_pool().connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ready"}
    except Exception as exc:
        log.error("readiness failed", extra={"fields": {"error": str(exc)}})
        return JSONResponse({"status": "not ready"}, status_code=503)


# ---------- shows & seat map ----------
@app.get("/shows")
def list_shows():
    with get_pool().connection() as conn:
        return conn.execute(
            "SELECT id, title, hall, starts_at FROM shows ORDER BY starts_at"
        ).fetchall()


@app.get("/shows/{show_id}/seats")
def seat_map(show_id: int):
    with get_pool().connection() as conn:
        if not conn.execute("SELECT 1 FROM shows WHERE id=%s", (show_id,)).fetchone():
            raise HTTPException(404, "show not found")
        return conn.execute(
            """
            SELECT s.label,
                   CASE WHEN b.id IS NOT NULL THEN 'BOOKED'
                        WHEN h.id IS NOT NULL THEN 'HELD'
                        ELSE 'AVAILABLE' END AS status
            FROM seats s
            LEFT JOIN bookings b ON b.seat_id = s.id AND b.status = 'CONFIRMED'
            LEFT JOIN holds h ON h.seat_id = s.id AND h.expires_at > now()
            WHERE s.show_id = %s ORDER BY s.id
            """,
            (show_id,),
        ).fetchall()


def lock_seat(conn, show_id: int, label: str) -> int:
    """Row-lock the seat so holds/bookings for it are serialized."""
    row = conn.execute(
        "SELECT id FROM seats WHERE show_id=%s AND label=%s FOR UPDATE",
        (show_id, label),
    ).fetchone()
    if not row:
        raise HTTPException(404, "seat not found for this show")
    return row["id"]


# ---------- holds ----------
class HoldRequest(BaseModel):
    seat: str


@app.post("/shows/{show_id}/holds", status_code=201)
def create_hold(show_id: int, body: HoldRequest):
    token = secrets.token_urlsafe(16)
    with get_pool().connection() as conn:
        seat_id = lock_seat(conn, show_id, body.seat)
        if conn.execute(
            "SELECT 1 FROM bookings WHERE seat_id=%s AND status='CONFIRMED'",
            (seat_id,),
        ).fetchone():
            raise HTTPException(409, "seat already booked")
        conn.execute(
            "DELETE FROM holds WHERE seat_id=%s AND expires_at <= now()", (seat_id,)
        )
        row = conn.execute(
            """
            INSERT INTO holds (seat_id, hold_token, expires_at)
            VALUES (%s, %s, now() + (%s::int * interval '1 second'))
            ON CONFLICT (seat_id) DO NOTHING
            RETURNING hold_token, expires_at
            """,
            (seat_id, token, hold_ttl()),
        ).fetchone()
        if not row:
            raise HTTPException(409, "seat is currently held")
    log.info("hold created", extra={"fields": {"show_id": show_id, "seat": body.seat}})
    return row


# ---------- bookings ----------
class BookingRequest(BaseModel):
    show_id: int
    seat: str
    hold_token: str


@app.post("/bookings", status_code=201)
def create_booking(body: BookingRequest):
    ticket_id = "TKT-" + secrets.token_hex(5).upper()
    try:
        with get_pool().connection() as conn:
            seat_id = lock_seat(conn, body.show_id, body.seat)
            hold = conn.execute(
                "SELECT id FROM holds WHERE seat_id=%s AND hold_token=%s AND expires_at > now()",
                (seat_id, body.hold_token),
            ).fetchone()
            if not hold:
                raise HTTPException(409, "hold missing, invalid or expired")
            row = conn.execute(
                """
                INSERT INTO bookings (ticket_id, show_id, seat_id, status)
                VALUES (%s, %s, %s, 'CONFIRMED')
                RETURNING ticket_id, show_id, status, created_at
                """,
                (ticket_id, body.show_id, seat_id),
            ).fetchone()
            conn.execute("DELETE FROM holds WHERE id=%s", (hold["id"],))
    except errors.UniqueViolation:
        # Safety net: the partial unique index rejected a double booking.
        raise HTTPException(409, "seat already booked")
    log.info("booking confirmed", extra={"fields": {"ticket_id": ticket_id}})
    return {**row, "seat": body.seat}


@app.get("/bookings/{ticket_id}")
def get_booking(ticket_id: str):
    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT ticket_id, show_id, status, created_at, cancelled_at FROM bookings WHERE ticket_id=%s",
            (ticket_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "booking not found")
    return row


@app.post("/bookings/{ticket_id}/cancel")
def cancel_booking(ticket_id: str):
    with get_pool().connection() as conn:
        row = conn.execute(
            """
            UPDATE bookings SET status='CANCELLED', cancelled_at=now()
            WHERE ticket_id=%s AND status='CONFIRMED'
            RETURNING ticket_id, status, cancelled_at
            """,
            (ticket_id,),
        ).fetchone()
        if not row:
            exists = conn.execute(
                "SELECT 1 FROM bookings WHERE ticket_id=%s", (ticket_id,)
            ).fetchone()
            if exists:
                raise HTTPException(409, "already cancelled")
            raise HTTPException(404, "booking not found")
    log.info("booking cancelled", extra={"fields": {"ticket_id": ticket_id}})
    return row

@app.get("/version")
def version():
    return {"version": os.environ.get("APP_VERSION", "unknown")}