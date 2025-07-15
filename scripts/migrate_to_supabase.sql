-- -----------------------------------------------------------------------------
-- migrate_to_supabase.sql – bootstrap schema for Supabase/pgvector integration
-- -----------------------------------------------------------------------------
-- This script is intended to be executed *once* on a fresh Supabase project.
-- You can run it via the Supabase SQL editor, psql, or any migration tool.
-- -----------------------------------------------------------------------------

-- 1. Extensions ----------------------------------------------------------------
create extension if not exists pgcrypto;   -- digest() for SHA-256 content_hash
create extension if not exists vector;     -- pgvector: embedding support

-- 2. Core table ----------------------------------------------------------------
-- Documents are tenant-scoped via project_id (UUID).  Exact-duplicate content is
-- avoided by a unique constraint on (project_id, content_hash).
create table if not exists documents (
    id            uuid primary key           default gen_random_uuid(),
    project_id    uuid           not null,   -- tenant / workspace identifier
    content       text           not null,
    embedding     vector(1536)   not null,   -- OpenAI text-embedding-3-small (1536-D)
    embedding_model text         not null,
    content_hash  bytea generated always as (digest(content, 'sha256')) stored,
    created_at    timestamptz    not null    default now(),
    unique (project_id, content_hash)
);

-- 3. Vector index --------------------------------------------------------------
-- ivfflat is generally faster than HNSW for ≤100M rows and is available on
-- Supabase Postgres 15.  Tune `lists` ≈ √(rowcount); start at 100.
create index if not exists documents_embedding_ivfflat
    on documents using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- 4. Row-Level Security (RLS) ---------------------------------------------------
-- By default Supabase enables RLS; ensure it’s on and restrict by project_id.
alter table documents enable row level security;

-- Allow CRUD when JWT claim `project_id` matches table.project_id.  The claim is
-- expected to be set by your auth hook; adjust as needed.
create policy "Project-based access"
    on documents for all
    using (project_id::text = current_setting('request.jwt.claims', true)::jsonb ->> 'project_id')
    with check (project_id::text = current_setting('request.jwt.claims', true)::jsonb ->> 'project_id');

-- 5. Similarity search RPC ------------------------------------------------------
-- Stored function `match_documents` wraps a parameterised cosine ANN query so
-- clients can call via Supabase’s `rpc()`.
create or replace function match_documents(
    query_embedding vector,
    match_count     int,
    project_id      uuid
)
returns table (
    id              uuid,
    content         text,
    embedding_model text,
    distance        float
) language sql stable as $$
    select d.id,
           d.content,
           d.embedding_model,
           (d.embedding <=> query_embedding) as distance
      from documents d
     where d.project_id = match_documents.project_id
  order by d.embedding <=> query_embedding
     limit match_documents.match_count;
$$;

-- 6. Maintenance reminder ------------------------------------------------------
-- For heavy ingest workloads automate `vacuum analyze` and periodic `reindex` on
-- `documents_embedding_ivfflat` to sustain query performance.

-- -----------------------------------------------------------------------------
-- End of migrate_to_supabase.sql
-- ----------------------------------------------------------------------------- 