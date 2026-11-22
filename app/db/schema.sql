-- app/db/schema.sql
-- One database for the whole assistant: knowledge (RAG), booking, and chat.
-- Safe to run again and again: every statement says IF NOT EXISTS.
-- The allowed values in the CHECK rules must match app/core/enums.py.

-- pgvector adds the "vector" column type. Session 7 stores the embeddings in it.
CREATE EXTENSION IF NOT EXISTS vector;


-- ---------------------------------------------------------------- knowledge (RAG)

CREATE TABLE IF NOT EXISTS documents (
    id           uuid        PRIMARY KEY,
    name         text        NOT NULL,                       -- the cleaned name, for showing only
    type         text        NOT NULL CHECK (type IN ('pdf', 'txt', 'md')),
    stored_as    text        NOT NULL UNIQUE,                -- our random file name on disk
    size_bytes   integer     NOT NULL CHECK (size_bytes > 0),
    sha256       char(64)    NOT NULL UNIQUE,                -- the same content can't be stored twice
    pages        integer     CHECK (pages > 0),
    uploaded_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id           bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id  uuid        NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    position     integer     NOT NULL CHECK (position >= 0), -- Chunk.index in Python: 0, 1, 2 ...
    text         text        NOT NULL CHECK (text <> ''),
    page         integer     CHECK (page > 0),
    section      text,
    UNIQUE (document_id, position)                           -- no two chunks in the same place
);


-- ---------------------------------------------------------------- booking

CREATE TABLE IF NOT EXISTS doctors (
    id           integer     PRIMARY KEY,                    -- the same ids as data/doctors.json
    name         text        NOT NULL,                       -- two doctors may share a name: no UNIQUE
    name_ar      text        NOT NULL,
    specialty    text        NOT NULL CHECK (specialty IN ('dermatology', 'pediatrics', 'internal-medicine', 'dentistry')),
    fee_egp      integer     NOT NULL CHECK (fee_egp > 0)
);

-- One row for every appointment time a doctor offers, on a real date
CREATE TABLE IF NOT EXISTS time_slots (
    id           bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    doctor_id    integer     NOT NULL REFERENCES doctors (id),
    starts_at    timestamptz NOT NULL,
    ends_at      timestamptz NOT NULL,
    CHECK (ends_at > starts_at),
    UNIQUE (doctor_id, starts_at)                            -- a doctor can't have the same slot twice
);

CREATE TABLE IF NOT EXISTS appointments (
    id               bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    reference        text        NOT NULL UNIQUE,            -- what the patient sees, like NFC-3F9A1C
    slot_id          bigint      NOT NULL REFERENCES time_slots (id),
    patient_name     text        NOT NULL,
    phone            text        NOT NULL,
    status           text        NOT NULL DEFAULT 'booked' CHECK (status IN ('booked', 'cancelled')),
    idempotency_key  text        UNIQUE,                     -- Session 6: a retried booking finds the first one
    created_at       timestamptz NOT NULL DEFAULT now()
);

-- The last guard against double booking: at most ONE booked appointment per slot.
-- Cancelled ones don't count, so a cancelled slot can be booked again.
CREATE UNIQUE INDEX IF NOT EXISTS one_booking_per_slot
    ON appointments (slot_id) WHERE status = 'booked';


-- ---------------------------------------------------------------- chat

CREATE TABLE IF NOT EXISTS conversations (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id               bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id  uuid        NOT NULL REFERENCES conversations (id) ON DELETE CASCADE,
    role             text        NOT NULL CHECK (role IN ('user', 'assistant')),
    content          text        NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now()
);

-- "Give me this conversation's messages in order" is the question we ask most
CREATE INDEX IF NOT EXISTS messages_by_conversation
    ON messages (conversation_id, id);
