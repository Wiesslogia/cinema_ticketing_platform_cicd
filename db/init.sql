CREATE TABLE shows (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  hall TEXT NOT NULL,
  starts_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE seats (
  id SERIAL PRIMARY KEY,
  show_id INT NOT NULL REFERENCES shows(id),
  label TEXT NOT NULL,
  UNIQUE (show_id, label)
);

-- Temporary hold: at most one row per seat (UNIQUE), expires via expires_at.
CREATE TABLE holds (
  id SERIAL PRIMARY KEY,
  seat_id INT NOT NULL UNIQUE REFERENCES seats(id),
  hold_token TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE bookings (
  id SERIAL PRIMARY KEY,
  ticket_id TEXT NOT NULL UNIQUE,
  show_id INT NOT NULL REFERENCES shows(id),
  seat_id INT NOT NULL REFERENCES seats(id),
  status TEXT NOT NULL CHECK (status IN ('CONFIRMED', 'CANCELLED')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  cancelled_at TIMESTAMPTZ
);

-- The core rule, enforced by the database: one CONFIRMED booking per seat.
CREATE UNIQUE INDEX one_confirmed_booking_per_seat
  ON bookings (seat_id) WHERE status = 'CONFIRMED';

INSERT INTO shows (title, hall, starts_at) VALUES
  ('Dune: Part Three', 'Hall 1', now() + interval '1 day'),
  ('Interstellar (Re-release)', 'Hall 2', now() + interval '2 days');

INSERT INTO seats (show_id, label)
SELECT s.id, r.rw || n.num::text
FROM shows s, unnest(ARRAY['A','B','C']) AS r(rw), generate_series(1, 8) AS n(num);
