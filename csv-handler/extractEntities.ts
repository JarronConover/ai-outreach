/**
 * Step 3 — Entity Extraction
 *
 * Applies the column mapping produced by detectColumnMappings() to every
 * CSV row and returns structured { company, person } objects.
 *
 * Only fields present in the column mapping (and therefore in the DB schema)
 * are extracted. No invented fields.
 */

import type { RawRow, ColumnMapping, ExtractedRow, CompanyData, PersonData, PersonStage } from "./types.js";

const VALID_STAGES = new Set<PersonStage>([
  "prospect",
  "contacted",
  "demo_scheduled",
  "demo_completed",
  "pricing",
  "onboarding",
  "client",
  "not_interested",
  "churned",
]);

function extractCompany(row: RawRow, mapping: ColumnMapping["company"]): CompanyData {
  const company: CompanyData = {};

  for (const [field, csvCol] of Object.entries(mapping)) {
    const value = row[csvCol];
    if (value === undefined || value === null || value === "") continue;

    if (field === "employee_count") {
      const num = parseInt(value.replace(/[^0-9]/g, ""), 10);
      if (!isNaN(num)) company.employee_count = num;
    } else {
      (company as Record<string, unknown>)[field] = value;
    }
  }

  return company;
}

function extractPerson(row: RawRow, mapping: ColumnMapping["person"]): PersonData {
  const person: PersonData = {};

  for (const [field, csvCol] of Object.entries(mapping)) {
    const value = row[csvCol];
    if (value === undefined || value === null || value === "") continue;

    if (field === "stage") {
      const lower = value.toLowerCase().replace(/[\s-]/g, "_") as PersonStage;
      person.stage = VALID_STAGES.has(lower) ? lower : "prospect";
    } else {
      (person as Record<string, unknown>)[field] = value;
    }
  }

  return person;
}

/**
 * Convert an array of raw CSV rows into structured ExtractedRow objects.
 * Rows that produce neither a company name nor a person name/email are skipped.
 */
export function extractEntities(rows: RawRow[], mapping: ColumnMapping): ExtractedRow[] {
  const extracted: ExtractedRow[] = [];

  for (const row of rows) {
    const company = extractCompany(row, mapping.company);
    const person = extractPerson(row, mapping.person);

    // Skip rows with no useful data
    const hasCompany = Boolean(company.name);
    const hasPerson = Boolean(person.name || person.email);
    if (!hasCompany && !hasPerson) continue;

    extracted.push({ company, person });
  }

  return extracted;
}
