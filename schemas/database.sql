-- AI-Outreach SDR System Database Schema
-- Current: Using Google Sheets, but this documents the structure for future SQL migration

-- Companies table
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    size VARCHAR(100),
    location VARCHAR(100),
    website VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- People table (Contacts/Prospects)
CREATE TABLE people (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    company_id UUID NOT NULL REFERENCES companies(id),
    email VARCHAR(255) NOT NULL,
    linkedin VARCHAR(255),
    phone VARCHAR(20),
    title VARCHAR(255) NOT NULL,
    stage VARCHAR(50) NOT NULL DEFAULT 'PROSPECTING'
        CHECK (stage IN ('PROSPECTING', 'INTERESTED', 'QUALIFIED', 'NEGOTIATING', 'WON', 'LOST')),
    last_response TIMESTAMP,
    last_contact TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast querying
CREATE INDEX idx_people_company_id ON people(company_id);
CREATE INDEX idx_people_stage ON people(stage);
CREATE INDEX idx_people_email ON people(email);
CREATE INDEX idx_people_last_contact ON people(last_contact);
