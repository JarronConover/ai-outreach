-- ============================================================
-- Fellowship CRM – initial schema migration
-- Run this in the Supabase SQL editor or via supabase db push
-- ============================================================

-- Reusable trigger that keeps updated_at current
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 1. companies
-- ============================================================
CREATE TABLE IF NOT EXISTS companies (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL,
    address         text,
    city            text,
    state           text,
    zip             text,
    phone           text,
    website         text,
    industry        text,
    employee_count  integer,
    created_at      timestamptz DEFAULT now() NOT NULL,
    updated_at      timestamptz DEFAULT now() NOT NULL
);

CREATE TRIGGER set_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 2. people  (references companies)
--
-- last_demo_id / next_demo_id removed — in SQL these are
-- derived via: SELECT * FROM demos WHERE people_id = X
-- ============================================================
CREATE TABLE IF NOT EXISTS people (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name                text NOT NULL,
    company_id          uuid REFERENCES companies(id) ON DELETE SET NULL,
    email               text UNIQUE NOT NULL,
    phone               text,
    linkedin            text,
    title               text,
    stage               text NOT NULL DEFAULT 'prospect'
        CHECK (stage IN (
            'prospect','contacted','demo_scheduled','demo_completed',
            'pricing','onboarding','client','not_interested','churned'
        )),
    last_response       text,
    last_contact        text,
    last_response_date  timestamptz,
    last_contact_date   timestamptz,
    created_at          timestamptz DEFAULT now() NOT NULL,
    updated_at          timestamptz DEFAULT now() NOT NULL
);

CREATE TRIGGER set_people_updated_at
    BEFORE UPDATE ON people
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 3. demos  (references people + companies)
-- ============================================================
CREATE TABLE IF NOT EXISTS demos (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    people_id   uuid NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    company_id  uuid REFERENCES companies(id) ON DELETE SET NULL,
    type        text NOT NULL DEFAULT 'discovery'
        CHECK (type IN ('discovery','tech','pricing','onboarding','client')),
    date        timestamptz,
    status      text NOT NULL DEFAULT 'scheduled'
        CHECK (status IN ('scheduled','completed','canceled','missed')),
    count       integer DEFAULT 0,
    event_id    text,   -- Google Calendar event ID (agent-managed, not a UUID)
    created_at  timestamptz DEFAULT now() NOT NULL,
    updated_at  timestamptz DEFAULT now() NOT NULL
);

CREATE TRIGGER set_demos_updated_at
    BEFORE UPDATE ON demos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 4. actions  (references people + demos; source_email_id FK
--    added after emails table is created)
-- ============================================================
CREATE TABLE IF NOT EXISTS actions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kind            text NOT NULL
        CHECK (kind IN ('email','calendar')),
    status          text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','confirming','confirmed','canceled')),
    created_at      timestamptz DEFAULT now() NOT NULL,
    confirmed_at    timestamptz,
    -- email-only fields
    email_type      text
        CHECK (email_type IN (
            'prospect_outreach','client_outreach','followup_email','demo_invite',
            'inbox_reply_interested','inbox_reply_not_interested','inbox_reply_demo_request'
        )),
    recipient_email text,
    recipient_name  text,
    subject         text,
    body            text,
    people_id       uuid REFERENCES people(id) ON DELETE SET NULL,
    -- calendar-only fields
    event_type      text
        CHECK (event_type IN (
            'demo_discovery','demo_tech','demo_pricing','demo_onboarding','demo_client'
        )),
    event_title     text,
    attendees       text[],
    start_time      timestamptz,
    end_time        timestamptz,
    demo_id         uuid REFERENCES demos(id) ON DELETE SET NULL,
    -- inbox reply link (FK added below after emails table exists)
    source_email_id uuid,
    updated_at      timestamptz DEFAULT now() NOT NULL
);

CREATE TRIGGER set_actions_updated_at
    BEFORE UPDATE ON actions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 5. emails  (inbox; references people + actions)
-- ============================================================
CREATE TABLE IF NOT EXISTS emails (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id          text UNIQUE NOT NULL,   -- Gmail message ID (not a UUID)
    from_email          text NOT NULL,
    from_name           text,
    people_id           uuid REFERENCES people(id) ON DELETE SET NULL,
    subject             text,
    body_snippet        text,
    received_at         timestamptz,
    category            text NOT NULL DEFAULT 'other'
        CHECK (category IN ('interested','not_interested','demo_request','manual','other')),
    status              text NOT NULL DEFAULT 'new'
        CHECK (status IN ('new','pending_response','responded','ignored')),
    response_action_id  uuid REFERENCES actions(id) ON DELETE SET NULL,
    note                text,
    created_at          timestamptz DEFAULT now() NOT NULL,
    updated_at          timestamptz DEFAULT now() NOT NULL
);

CREATE TRIGGER set_emails_updated_at
    BEFORE UPDATE ON emails
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Resolve the actions → emails circular FK now that emails exists
ALTER TABLE actions
    ADD CONSTRAINT actions_source_email_id_fkey
    FOREIGN KEY (source_email_id) REFERENCES emails(id) ON DELETE SET NULL;

-- ============================================================
-- Indexes for common query patterns
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_people_company_id    ON people(company_id);
CREATE INDEX IF NOT EXISTS idx_people_stage         ON people(stage);
CREATE INDEX IF NOT EXISTS idx_people_email         ON people(email);
CREATE INDEX IF NOT EXISTS idx_demos_people_id      ON demos(people_id);
CREATE INDEX IF NOT EXISTS idx_demos_company_id     ON demos(company_id);
CREATE INDEX IF NOT EXISTS idx_demos_status         ON demos(status);
CREATE INDEX IF NOT EXISTS idx_actions_status       ON actions(status);
CREATE INDEX IF NOT EXISTS idx_actions_people_id    ON actions(people_id);
CREATE INDEX IF NOT EXISTS idx_emails_people_id     ON emails(people_id);
CREATE INDEX IF NOT EXISTS idx_emails_category      ON emails(category);
CREATE INDEX IF NOT EXISTS idx_emails_status        ON emails(status);
