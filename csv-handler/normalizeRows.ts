/**
 * Step 4 — Normalization
 *
 * Cleans every field value before writing to the database:
 *   - Trims whitespace
 *   - Normalizes email addresses (lowercase)
 *   - Normalizes phone numbers (digits + +, -, (, ), space only)
 *   - Normalizes URLs (ensures https:// prefix for linkedin/website)
 *   - Converts obviously empty/invalid values to undefined
 *   - Validates ISO date strings
 */

import type { ExtractedRow, CompanyData, PersonData } from "./types.js";

// ─── helpers ──────────────────────────────────────────────────────────────────

function str(v: unknown): string | undefined {
  if (v === null || v === undefined) return undefined;
  const s = String(v).trim();
  return s === "" ? undefined : s;
}

function email(v: unknown): string | undefined {
  const s = str(v);
  if (!s) return undefined;
  const lower = s.toLowerCase();
  // Basic sanity check — must contain @ and a dot after @
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(lower) ? lower : undefined;
}

function phone(v: unknown): string | undefined {
  const s = str(v);
  if (!s) return undefined;
  // Keep only digit-friendly chars
  const cleaned = s.replace(/[^\d+\-().  ]/g, "").trim();
  // Must have at least 7 digits
  return (cleaned.replace(/\D/g, "").length >= 7) ? cleaned : undefined;
}

function url(v: unknown): string | undefined {
  const s = str(v);
  if (!s) return undefined;
  if (/^https?:\/\//i.test(s)) return s;
  // Add https:// if it looks like a URL
  if (s.includes(".") && !s.includes(" ")) return `https://${s}`;
  return undefined;
}

function isoDate(v: unknown): string | undefined {
  const s = str(v);
  if (!s) return undefined;
  // Accept YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    const d = new Date(s);
    return isNaN(d.getTime()) ? undefined : s;
  }
  // Try parsing common US formats and convert to ISO
  const d = new Date(s);
  if (!isNaN(d.getTime())) {
    return d.toISOString().slice(0, 10); // YYYY-MM-DD
  }
  return undefined;
}

// ─── normalizers ──────────────────────────────────────────────────────────────

function normalizeCompany(c: CompanyData): CompanyData {
  return {
    name: str(c.name),
    address: str(c.address),
    city: str(c.city),
    state: str(c.state),
    zip: str(c.zip),
    phone: phone(c.phone),
    website: url(c.website),
    industry: str(c.industry),
    employee_count: c.employee_count ?? undefined,
  };
}

function normalizePerson(p: PersonData): PersonData {
  return {
    name: str(p.name),
    email: email(p.email),
    phone: phone(p.phone),
    linkedin: url(p.linkedin),
    title: str(p.title),
    stage: p.stage ?? "prospect",
    last_response: str(p.last_response),
    last_contact: str(p.last_contact),
    last_response_date: isoDate(p.last_response_date),
    last_contact_date: isoDate(p.last_contact_date),
  };
}

/** Remove keys whose value is undefined to keep Supabase payloads clean. */
function dropUndefined<T extends object>(obj: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(obj).filter(([, v]) => v !== undefined),
  ) as Partial<T>;
}

/**
 * Normalize an array of extracted rows in-place.
 * Returns a new array; original rows are not mutated.
 */
export function normalizeRows(rows: ExtractedRow[]): ExtractedRow[] {
  return rows.map(({ company, person }) => ({
    company: dropUndefined(normalizeCompany(company)) as CompanyData,
    person: dropUndefined(normalizePerson(person)) as PersonData,
  }));
}
