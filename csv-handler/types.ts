/** Raw row parsed from CSV — column names preserved as-is. */
export type RawRow = Record<string, string>;

/** Allowed stage values for the people.stage column. */
export type PersonStage =
  | "prospect"
  | "contacted"
  | "demo_scheduled"
  | "demo_completed"
  | "pricing"
  | "onboarding"
  | "client"
  | "not_interested"
  | "churned";

/** Fields that exist in the `companies` Supabase table. */
export interface CompanyData {
  name?: string;
  address?: string;
  city?: string;
  state?: string;
  zip?: string;
  phone?: string;
  website?: string;
  industry?: string;
  employee_count?: number | null;
}

/** Fields that exist in the `people` Supabase table (excluding company_id, which is resolved separately). */
export interface PersonData {
  name?: string;
  email?: string;
  phone?: string;
  linkedin?: string;
  title?: string;
  stage?: PersonStage;
  last_response?: string;
  last_contact?: string;
  last_response_date?: string | null;
  last_contact_date?: string | null;
}

/** A single extracted row containing one company and one person. */
export interface ExtractedRow {
  company: CompanyData;
  person: PersonData;
}

/**
 * Maps database field names to CSV column names.
 * e.g. { person: { name: "Full Name", email: "Email Address" }, company: { name: "Company" } }
 */
export interface ColumnMapping {
  person: Partial<Record<keyof PersonData, string>>;
  company: Partial<Record<keyof CompanyData, string>>;
}

/** Final result returned from processCSV(). */
export interface ProcessResult {
  rowsRead: number;
  companiesUpserted: number;
  peopleUpserted: number;
  errors: string[];
}

/** A single upsert outcome for logging/debugging. */
export interface UpsertOutcome {
  key: string;
  action: "inserted" | "updated" | "skipped";
  error?: string;
}
