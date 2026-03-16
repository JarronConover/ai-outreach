/**
 * Step 7 — Upsert People
 *
 * For each row that has a person:
 *   1. Identify the person by email (preferred) or name + company
 *   2. If the person exists → update fields that are currently empty in the DB
 *   3. If the person does not exist → insert
 *   4. Link the person to their company if both exist
 *
 * Requires the companyMap returned by upsertCompanies().
 */

import type { SupabaseClient } from "@supabase/supabase-js";
import type { ExtractedRow, PersonData, UpsertOutcome } from "./types.js";

interface DbPerson {
  id: string;
  name: string | null;
  company_id: string | null;
  email: string | null;
  phone: string | null;
  linkedin: string | null;
  title: string | null;
  stage: string | null;
  last_response: string | null;
  last_contact: string | null;
  last_response_date: string | null;
  last_contact_date: string | null;
}

/** Build a patch of fields that are null in the DB but present in incoming data. */
function buildPatch(
  existing: DbPerson,
  incoming: PersonData,
  companyId: string | undefined,
): Partial<PersonData & { company_id?: string }> {
  const patch: Partial<PersonData & { company_id?: string }> = {};

  const fields: (keyof PersonData)[] = [
    "name", "email", "phone", "linkedin", "title", "stage",
    "last_response", "last_contact", "last_response_date", "last_contact_date",
  ];

  for (const field of fields) {
    const current = (existing as unknown as Record<string, unknown>)[field];
    const next = incoming[field];
    if ((current === null || current === undefined || current === "") && next !== undefined && next !== null) {
      (patch as Record<string, unknown>)[field] = next;
    }
  }

  // Link to company if not yet linked
  if (!existing.company_id && companyId) {
    patch.company_id = companyId;
  }

  return patch;
}

/**
 * Upsert all people found in the extracted rows.
 *
 * @param rows - Normalized + enriched extracted rows
 * @param companyMap - Map<lowerCaseName, companyId> from upsertCompanies()
 * @param supabase - Supabase client
 */
export async function upsertPeople(
  rows: ExtractedRow[],
  companyMap: Map<string, string>,
  supabase: SupabaseClient,
): Promise<UpsertOutcome[]> {
  const outcomes: UpsertOutcome[] = [];

  // Deduplicate by email (primary key) or by name+company
  const seen = new Map<string, { person: PersonData; companyName: string | undefined }>();

  for (const { person, company } of rows) {
    if (!person.name && !person.email) continue;

    const dedupeKey = person.email
      ? `email:${person.email.toLowerCase()}`
      : `name:${(person.name ?? "").toLowerCase()}:${(company.name ?? "").toLowerCase()}`;

    if (!seen.has(dedupeKey)) {
      seen.set(dedupeKey, { person, companyName: company.name });
    }
  }

  for (const [, { person, companyName }] of seen) {
    const label = person.email ?? person.name ?? "(unknown)";
    const companyId = companyName ? companyMap.get(companyName.toLowerCase().trim()) : undefined;

    try {
      let existing: DbPerson | null = null;

      // 1a. Lookup by email
      if (person.email) {
        const { data, error } = await supabase
          .from("people")
          .select("*")
          .eq("email", person.email)
          .maybeSingle();
        if (error) throw new Error(error.message);
        existing = data as DbPerson | null;
      }

      // 1b. Fallback lookup by name + company_id
      if (!existing && person.name && companyId) {
        const { data, error } = await supabase
          .from("people")
          .select("*")
          .ilike("name", person.name)
          .eq("company_id", companyId)
          .maybeSingle();
        if (error) throw new Error(error.message);
        existing = data as DbPerson | null;
      }

      if (existing) {
        // 2. Update missing fields
        const patch = buildPatch(existing, person, companyId);
        if (Object.keys(patch).length > 0) {
          const { error: updateErr } = await supabase
            .from("people")
            .update(patch)
            .eq("id", existing.id);
          if (updateErr) throw new Error(updateErr.message);
        }
        outcomes.push({ key: label, action: "updated" });
      } else {
        // 3. Insert new person
        const payload: Record<string, unknown> = { ...person };
        if (companyId) payload.company_id = companyId;
        if (!payload.stage) payload.stage = "prospect";

        const { error: insertErr } = await supabase.from("people").insert(payload);
        if (insertErr) throw new Error(insertErr.message);
        outcomes.push({ key: label, action: "inserted" });
      }
    } catch (err) {
      outcomes.push({ key: label, action: "skipped", error: String(err) });
    }
  }

  return outcomes;
}
