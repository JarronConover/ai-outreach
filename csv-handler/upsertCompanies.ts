/**
 * Step 6 — Upsert Companies
 *
 * For each row that has a company name:
 *   1. Check if the company already exists (case-insensitive name match)
 *   2. If it exists → update fields that are currently empty in the DB
 *   3. If it does not exist → insert a new row
 *
 * Returns a Map of company name (lowercased) → company UUID so that
 * upsertPeople() can link people to their companies.
 */

import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import type { ExtractedRow, CompanyData, UpsertOutcome } from "./types.js";

interface DbCompany {
  id: string;
  name: string;
  address: string | null;
  city: string | null;
  state: string | null;
  zip: string | null;
  phone: string | null;
  website: string | null;
  industry: string | null;
  employee_count: number | null;
}

/** Build a patch object: only fields that are null/empty in the DB but present in the new data. */
function buildPatch(existing: DbCompany, incoming: CompanyData): Partial<CompanyData> {
  const patch: Partial<CompanyData> = {};

  const fillIfMissing = (field: keyof CompanyData) => {
    const current = (existing as unknown as Record<string, unknown>)[field];
    const next = incoming[field];
    if ((current === null || current === undefined || current === "") && next !== undefined && next !== null) {
      (patch as Record<string, unknown>)[field] = next;
    }
  };

  (["address", "city", "state", "zip", "phone", "website", "industry", "employee_count"] as const).forEach(
    fillIfMissing,
  );

  return patch;
}

/**
 * Upsert all companies found in the extracted rows.
 *
 * @returns Map<lowerCaseName, companyId>
 */
export async function upsertCompanies(
  rows: ExtractedRow[],
  supabase: SupabaseClient,
): Promise<{ companyMap: Map<string, string>; outcomes: UpsertOutcome[] }> {
  const companyMap = new Map<string, string>();
  const outcomes: UpsertOutcome[] = [];

  // Deduplicate companies by lowercased name (process each name once)
  const seen = new Map<string, CompanyData>();
  for (const { company } of rows) {
    if (!company.name) continue;
    const key = company.name.toLowerCase().trim();
    if (!seen.has(key)) seen.set(key, company);
  }

  for (const [key, company] of seen) {
    try {
      // 1. Check if company exists
      const { data: existing, error: fetchErr } = await supabase
        .from("companies")
        .select("*")
        .ilike("name", company.name!)
        .maybeSingle();

      if (fetchErr) throw new Error(fetchErr.message);

      if (existing) {
        // 2. Update missing fields
        const patch = buildPatch(existing as DbCompany, company);
        if (Object.keys(patch).length > 0) {
          const { error: updateErr } = await supabase
            .from("companies")
            .update(patch)
            .eq("id", (existing as DbCompany).id);
          if (updateErr) throw new Error(updateErr.message);
        }
        companyMap.set(key, (existing as DbCompany).id);
        outcomes.push({ key: company.name!, action: "updated" });
      } else {
        // 3. Insert new company
        const { data: inserted, error: insertErr } = await supabase
          .from("companies")
          .insert({ ...company })
          .select("id")
          .single();

        if (insertErr) throw new Error(insertErr.message);
        companyMap.set(key, (inserted as { id: string }).id);
        outcomes.push({ key: company.name!, action: "inserted" });
      }
    } catch (err) {
      outcomes.push({ key: company.name!, action: "skipped", error: String(err) });
    }
  }

  return { companyMap, outcomes };
}
