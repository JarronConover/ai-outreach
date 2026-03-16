/**
 * Database schema definitions — single source of truth for column names
 * and types that the LLM and upsert logic are allowed to reference.
 *
 * These match exactly the Supabase migration in
 *   supabase/migrations/20260305000000_create_crm_tables.sql
 *
 * To fetch schemas dynamically from the Supabase OpenAPI spec instead,
 * call `fetchSchemaFromSupabase()` and pass the result to the LLM prompt.
 */

import { createClient } from "@supabase/supabase-js";

export interface FieldDef {
  name: string;
  type: string;
  required: boolean;
  description?: string;
}

/** Writable fields for the `companies` table (auto-cols excluded). */
export const COMPANIES_SCHEMA: FieldDef[] = [
  { name: "name", type: "text", required: true, description: "Company or organisation name" },
  { name: "address", type: "text", required: false, description: "Street address" },
  { name: "city", type: "text", required: false },
  { name: "state", type: "text", required: false, description: "US state abbreviation or full name" },
  { name: "zip", type: "text", required: false, description: "Postal / ZIP code" },
  { name: "phone", type: "text", required: false, description: "Main phone number" },
  { name: "website", type: "text", required: false, description: "Company website URL" },
  { name: "industry", type: "text", required: false, description: "Industry or vertical (e.g. Construction, SaaS)" },
  {
    name: "employee_count",
    type: "integer",
    required: false,
    description: "Approximate number of employees (integer)",
  },
];

/** Writable fields for the `people` table (auto-cols and company_id excluded). */
export const PEOPLE_SCHEMA: FieldDef[] = [
  { name: "name", type: "text", required: true, description: "Full name of the person" },
  { name: "email", type: "text", required: false, description: "Business email address (unique key)" },
  { name: "phone", type: "text", required: false, description: "Direct phone number" },
  {
    name: "linkedin",
    type: "text",
    required: false,
    description: "LinkedIn profile URL (e.g. https://linkedin.com/in/handle)",
  },
  { name: "title", type: "text", required: false, description: "Job title / role (e.g. CTO, VP Engineering)" },
  {
    name: "stage",
    type: "text",
    required: false,
    description:
      "CRM stage. One of: prospect | contacted | demo_scheduled | demo_completed | pricing | onboarding | client | not_interested | churned. Default: prospect",
  },
  {
    name: "last_response",
    type: "text",
    required: false,
    description: "Type of last response from this person (e.g. email, call)",
  },
  {
    name: "last_contact",
    type: "text",
    required: false,
    description: "Type of last outreach to this person (e.g. email, call)",
  },
  {
    name: "last_response_date",
    type: "date",
    required: false,
    description: "ISO 8601 date of last response (YYYY-MM-DD)",
  },
  {
    name: "last_contact_date",
    type: "date",
    required: false,
    description: "ISO 8601 date of last contact (YYYY-MM-DD)",
  },
];

/** Human-readable schema description formatted for LLM prompts. */
export function schemaToPromptText(fields: FieldDef[], tableName: string): string {
  const lines = fields.map((f) => {
    const req = f.required ? " [REQUIRED]" : "";
    const desc = f.description ? ` — ${f.description}` : "";
    return `  - ${f.name} (${f.type})${req}${desc}`;
  });
  return `Table: ${tableName}\n${lines.join("\n")}`;
}

/**
 * Optionally fetch table schemas directly from the Supabase OpenAPI spec.
 * Falls back to the hardcoded definitions above if the request fails.
 */
export async function fetchSchemaFromSupabase(
  supabaseUrl: string,
  supabaseKey: string,
): Promise<{ companies: FieldDef[]; people: FieldDef[] }> {
  try {
    const res = await fetch(`${supabaseUrl}/rest/v1/`, {
      headers: { apikey: supabaseKey, Authorization: `Bearer ${supabaseKey}` },
    });
    if (!res.ok) throw new Error(`OpenAPI fetch failed: ${res.status}`);

    const spec = (await res.json()) as {
      definitions?: Record<string, { properties?: Record<string, { type?: string; description?: string }> }>;
    };

    const parseTable = (tableName: string): FieldDef[] => {
      const def = spec.definitions?.[tableName];
      if (!def?.properties) return [];
      const autoFields = new Set(["id", "created_at", "updated_at"]);
      return Object.entries(def.properties)
        .filter(([col]) => !autoFields.has(col))
        .map(([col, meta]) => ({
          name: col,
          type: meta.type ?? "text",
          required: false,
          description: meta.description,
        }));
    };

    const companies = parseTable("companies");
    const people = parseTable("people");

    return {
      companies: companies.length ? companies : COMPANIES_SCHEMA,
      people: people.length ? people : PEOPLE_SCHEMA,
    };
  } catch {
    // Fall back to hardcoded schemas
    return { companies: COMPANIES_SCHEMA, people: PEOPLE_SCHEMA };
  }
}
