-- app/db/schema.sql
-- One database for the whole assistant: knowledge, booking and chat.
-- "IF NOT EXISTS" makes it safe to run this file again and again.

-- pgvector: Session 7 stores the chunks' embeddings with it
CREATE EXTENSION IF NOT EXISTS vector;

-- ===== Knowledge: the documents from Session 4, and their chunks =====
CREATE TABLE IF NOT EXISTS documents (
    id           uuid PRIMARY KEY,
    name         text NOT NULL,
    type         text NOT NULL CHECK (type IN ('pdf', 'txt', 'md')),
    sha256       text NOT NULL UNIQUE,              -- the same file can't be stored twice
    uploaded_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id           serial PRIMARY KEY,
    document_id  uuid NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    position     integer NOT NULL,                  -- 0, 1, 2 ... inside its document
    text         text NOT NULL,
    page         integer,
    section      text
);

-- ===== Booking: doctors, their time slots, and appointments =====
CREATE TABLE IF NOT EXISTS doctors (
    id         integer PRIMARY KEY,                 -- the same ids as data/doctors.json
    name       text NOT NULL,
    name_ar    text NOT NULL,
    specialty  text NOT NULL,
    fee_egp    integer NOT NULL CHECK (fee_egp > 0)
);

CREATE TABLE IF NOT EXISTS time_slots (
    id         serial PRIMARY KEY,
    doctor_id  integer NOT NULL REFERENCES doctors (id),
    starts_at  timestamptz NOT NULL,
    UNIQUE (doctor_id, starts_at)                   -- a doctor can't have the same slot twice
);

CREATE TABLE IF NOT EXISTS appointments (
    id            serial PRIMARY KEY,
    reference     text NOT NULL UNIQUE,             -- what the patient sees, like NFC-3F9A1C
    slot_id       integer NOT NULL REFERENCES time_slots (id),
    patient_name  text NOT NULL,
    phone         text NOT NULL,
    status        text NOT NULL DEFAULT 'booked' CHECK (status IN ('booked', 'cancelled'))
);

-- At most ONE booked appointment per slot. Cancelled ones don't count.
CREATE UNIQUE INDEX IF NOT EXISTS one_booking_per_slot
    ON appointments (slot_id) WHERE status = 'booked';

-- ===== Chat: conversations and their messages =====
CREATE TABLE IF NOT EXISTS conversations (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id               serial PRIMARY KEY,
    conversation_id  uuid NOT NULL REFERENCES conversations (id) ON DELETE CASCADE,
    role             text NOT NULL CHECK (role IN ('user', 'assistant')),
    content          text NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now()
);
