import os
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def clean_db():
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as c:
        c.execute("TRUNCATE holds, bookings RESTART IDENTITY")
    yield


def client():
    return TestClient(app)


def hold(seat="A1", show=1):
    return client().post(f"/shows/{show}/holds", json={"seat": seat})


def test_health_and_ready():
    assert client().get("/health").status_code == 200
    assert client().get("/ready").status_code == 200


def test_seed_data():
    assert len(client().get("/shows").json()) == 2
    seats = client().get("/shows/1/seats").json()
    assert len(seats) == 24 and all(s["status"] == "AVAILABLE" for s in seats)


def test_full_flow_and_cancel():
    token = hold().json()["hold_token"]
    r = client().post(
        "/bookings", json={"show_id": 1, "seat": "A1", "hold_token": token}
    )
    assert r.status_code == 201
    ticket = r.json()["ticket_id"]
    assert ticket.startswith("TKT-")
    assert hold().status_code == 409  # booked
    assert client().post(f"/bookings/{ticket}/cancel").status_code == 200
    assert client().post(f"/bookings/{ticket}/cancel").status_code == 409
    assert hold().status_code == 201  # seat free again


def test_concurrent_holds_only_one_wins():
    with ThreadPoolExecutor(max_workers=20) as ex:
        codes = list(ex.map(lambda _: hold("B2").status_code, range(20)))
    assert codes.count(201) == 1
    assert codes.count(409) == 19


def test_concurrent_confirm_same_hold_only_one_booking():
    token = hold("C3").json()["hold_token"]
    body = {"show_id": 1, "seat": "C3", "hold_token": token}
    with ThreadPoolExecutor(max_workers=10) as ex:
        codes = list(
            ex.map(
                lambda _: client().post("/bookings", json=body).status_code, range(10)
            )
        )
    assert codes.count(201) == 1


def test_expired_hold_cannot_confirm_and_seat_reopens():
    token = hold("A2").json()["hold_token"]
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as c:
        c.execute("UPDATE holds SET expires_at = now() - interval '1 second'")
    r = client().post(
        "/bookings", json={"show_id": 1, "seat": "A2", "hold_token": token}
    )
    assert r.status_code == 409
    assert hold("A2").status_code == 201
