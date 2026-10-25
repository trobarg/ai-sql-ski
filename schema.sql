-- Ski resort database: lifts, runs, guests, season passes, lift scans, and lessons.
-- Each group member can "own" one or two tables (see README).

CREATE TABLE lift (
    lift_id      INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    lift_type    TEXT NOT NULL CHECK (lift_type IN ('chair', 'gondola', 'tram', 'surface')),
    seats        INTEGER NOT NULL,          -- people per chair/cabin
    vertical_ft  INTEGER NOT NULL,          -- vertical rise in feet
    is_open      INTEGER NOT NULL DEFAULT 1 -- 1 = open today, 0 = closed
);

CREATE TABLE run (
    run_id       INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    lift_id      INTEGER NOT NULL REFERENCES lift(lift_id),  -- lift that serves this run
    difficulty   TEXT NOT NULL CHECK (difficulty IN ('green', 'blue', 'black', 'double black')),
    length_ft    INTEGER NOT NULL,
    is_groomed   INTEGER NOT NULL DEFAULT 0  -- 1 = groomed today
);

CREATE TABLE pass_type (
    pass_type_id INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,             -- e.g. 'Season Adult', 'Day Ticket'
    price        REAL NOT NULL              -- USD
);

CREATE TABLE guest (
    guest_id     INTEGER PRIMARY KEY,
    first_name   TEXT NOT NULL,
    last_name    TEXT NOT NULL,
    birth_year   INTEGER NOT NULL,
    home_state   TEXT NOT NULL,             -- two-letter code, e.g. 'UT'
    skill_level  TEXT NOT NULL CHECK (skill_level IN ('beginner', 'intermediate', 'advanced', 'expert'))
);

CREATE TABLE pass (
    pass_id       INTEGER PRIMARY KEY,
    guest_id      INTEGER NOT NULL REFERENCES guest(guest_id),
    pass_type_id  INTEGER NOT NULL REFERENCES pass_type(pass_type_id),
    purchase_date TEXT NOT NULL             -- 'YYYY-MM-DD'
);

CREATE TABLE lift_scan (
    scan_id    INTEGER PRIMARY KEY,
    pass_id    INTEGER NOT NULL REFERENCES pass(pass_id),
    lift_id    INTEGER NOT NULL REFERENCES lift(lift_id),
    scan_time  TEXT NOT NULL                -- 'YYYY-MM-DD HH:MM:SS'
);

CREATE TABLE instructor (
    instructor_id INTEGER PRIMARY KEY,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    discipline    TEXT NOT NULL CHECK (discipline IN ('ski', 'snowboard')),
    hourly_rate   REAL NOT NULL             -- USD per hour
);

CREATE TABLE lesson (
    lesson_id     INTEGER PRIMARY KEY,
    instructor_id INTEGER NOT NULL REFERENCES instructor(instructor_id),
    guest_id      INTEGER NOT NULL REFERENCES guest(guest_id),
    lesson_date   TEXT NOT NULL,            -- 'YYYY-MM-DD'
    hours         REAL NOT NULL
);
