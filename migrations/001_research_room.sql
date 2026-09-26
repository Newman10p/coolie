-- PostgreSQL schema for the durable adapters introduced after the in-memory test implementation.
CREATE TABLE research_missions (mission_id TEXT PRIMARY KEY, status TEXT NOT NULL, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL);
CREATE TABLE research_tasks (task_id TEXT PRIMARY KEY, mission_id TEXT NOT NULL REFERENCES research_missions(mission_id), status TEXT NOT NULL, payload JSONB NOT NULL);
CREATE INDEX research_tasks_mission_idx ON research_tasks(mission_id);
CREATE TABLE source_snapshots (snapshot_id TEXT PRIMARY KEY, mission_id TEXT NOT NULL REFERENCES research_missions(mission_id), task_id TEXT NOT NULL REFERENCES research_tasks(task_id), source_reference TEXT NOT NULL, retrieved_at TIMESTAMPTZ NOT NULL, content_hash TEXT NOT NULL, artifact_key TEXT NOT NULL UNIQUE, source_quality DOUBLE PRECISION NOT NULL);
CREATE TABLE evidence_records (evidence_id TEXT PRIMARY KEY, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL);
CREATE TABLE opportunities (opportunity_id TEXT PRIMARY KEY, mission_id TEXT NOT NULL REFERENCES research_missions(mission_id), payload JSONB NOT NULL);
CREATE TABLE research_reports (report_id TEXT PRIMARY KEY, mission_id TEXT NOT NULL REFERENCES research_missions(mission_id), created_at TIMESTAMPTZ NOT NULL, artifact_key TEXT NOT NULL UNIQUE, content_hash TEXT NOT NULL);
CREATE TABLE audit_events (event_id BIGSERIAL PRIMARY KEY, mission_id TEXT NOT NULL, recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, payload JSONB NOT NULL);
CREATE INDEX audit_events_mission_idx ON audit_events(mission_id, recorded_at);
CREATE TABLE sector_configurations (version TEXT PRIMARY KEY, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
