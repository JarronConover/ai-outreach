/**
 * Step 8 — Main Pipeline
 *
 * Orchestrates the full CSV ingestion flow:
 *
 *   parseCsv
 *   → detectColumnMappings  (LLM)
 *   → extractEntities
 *   → normalizeRows
 *   → enrichData            (LLM, batched 15 rows)
 *   → upsertCompanies
 *   → upsertPeople
 *
 * Can be used as a library (import processCSV) or as a CLI:
 *   npx tsx processCsv.ts path/to/file.csv
 */

import { readFileSync } from "fs";
import { createClient } from "@supabase/supabase-js";
import "dotenv/config";

import { parseCsv } from "./parseCsv.js";
import { detectColumnMappings } from "./detectColumnMappings.js";
import { extractEntities } from "./extractEntities.js";
import { normalizeRows } from "./normalizeRows.js";
import { enrichData } from "./enrichData.js";
import { upsertCompanies } from "./upsertCompanies.js";
import { upsertPeople } from "./upsertPeople.js";
import { fetchSchemaFromSupabase } from "./schema.js";
import type { ProcessResult } from "./types.js";

// ─── environment ──────────────────────────────────────────────────────────────

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

// ─── main pipeline ────────────────────────────────────────────────────────────

export async function processCSV(csvContent: string, options?: { skipEnrichment?: boolean }): Promise<ProcessResult> {
  const supabaseUrl = requireEnv("SUPABASE_URL");
  const supabaseKey = requireEnv("SUPABASE_KEY");
  const googleApiKey = requireEnv("GOOGLE_API_KEY");

  const supabase = createClient(supabaseUrl, supabaseKey);
  const errors: string[] = [];

  // ── Step 1: Parse CSV ──────────────────────────────────────────────────────
  console.log("→ Parsing CSV...");
  const { rows: rawRows, headers, errors: parseErrors } = parseCsv(csvContent);
  errors.push(...parseErrors);

  if (rawRows.length === 0) {
    return { rowsRead: 0, companiesUpserted: 0, peopleUpserted: 0, errors: ["No rows found in CSV."] };
  }
  console.log(`  ${rawRows.length} rows, ${headers.length} columns`);

  // ── Load schemas (dynamic from Supabase, falls back to hardcoded) ──────────
  console.log("→ Loading database schemas...");
  const { companies: companiesSchema, people: peopleSchema } = await fetchSchemaFromSupabase(
    supabaseUrl,
    supabaseKey,
  );

  // ── Step 2: Detect column mappings ────────────────────────────────────────
  console.log("→ Detecting column mappings (LLM)...");
  const mapping = await detectColumnMappings(headers, rawRows, companiesSchema, peopleSchema, googleApiKey);
  console.log("  Person fields mapped:", Object.keys(mapping.person).join(", ") || "(none)");
  console.log("  Company fields mapped:", Object.keys(mapping.company).join(", ") || "(none)");

  if (Object.keys(mapping.person).length === 0 && Object.keys(mapping.company).length === 0) {
    return {
      rowsRead: rawRows.length,
      companiesUpserted: 0,
      peopleUpserted: 0,
      errors: ["LLM could not map any CSV columns to known database fields."],
    };
  }

  // ── Step 3: Extract entities ──────────────────────────────────────────────
  console.log("→ Extracting entities...");
  const extracted = extractEntities(rawRows, mapping);
  console.log(`  ${extracted.length} rows with extractable data`);

  // ── Step 4: Normalize ──────────────────────────────────────────────────────
  console.log("→ Normalizing...");
  const normalized = normalizeRows(extracted);

  // ── Step 5: Enrich (optional) ─────────────────────────────────────────────
  let enriched = normalized;
  if (!options?.skipEnrichment) {
    console.log("→ Enriching data with LLM (batches of 15)...");
    try {
      enriched = await enrichData(normalized, companiesSchema, peopleSchema, googleApiKey);
    } catch (err) {
      const msg = `Enrichment step failed (continuing with normalized data): ${String(err)}`;
      console.warn(msg);
      errors.push(msg);
    }
  }

  // ── Step 6: Upsert companies ───────────────────────────────────────────────
  console.log("→ Upserting companies...");
  const { companyMap, outcomes: companyOutcomes } = await upsertCompanies(enriched, supabase);

  let companiesUpserted = 0;
  for (const o of companyOutcomes) {
    if (o.error) {
      errors.push(`Company "${o.key}": ${o.error}`);
    } else {
      companiesUpserted++;
      console.log(`  [${o.action}] ${o.key}`);
    }
  }

  // ── Step 7: Upsert people ─────────────────────────────────────────────────
  console.log("→ Upserting people...");
  const personOutcomes = await upsertPeople(enriched, companyMap, supabase);

  let peopleUpserted = 0;
  for (const o of personOutcomes) {
    if (o.error) {
      errors.push(`Person "${o.key}": ${o.error}`);
    } else {
      peopleUpserted++;
      console.log(`  [${o.action}] ${o.key}`);
    }
  }

  // ── Summary ───────────────────────────────────────────────────────────────
  const result: ProcessResult = {
    rowsRead: rawRows.length,
    companiesUpserted,
    peopleUpserted,
    errors,
  };

  console.log("\n── Summary ──────────────────────────────────");
  console.log(`  Rows read:           ${result.rowsRead}`);
  console.log(`  Companies upserted:  ${result.companiesUpserted}`);
  console.log(`  People upserted:     ${result.peopleUpserted}`);
  if (result.errors.length > 0) {
    console.log(`  Errors (${result.errors.length}):`);
    result.errors.forEach((e) => console.log(`    • ${e}`));
  }
  console.log("─────────────────────────────────────────────\n");

  return result;
}

// ─── CLI entry point ──────────────────────────────────────────────────────────

if (process.argv[1] && process.argv[1].endsWith("processCsv.ts")) {
  const filePath = process.argv[2];
  if (!filePath) {
    console.error("Usage: npx tsx processCsv.ts <path-to-csv>");
    process.exit(1);
  }

  let content: string;
  try {
    content = readFileSync(filePath, "utf-8");
  } catch (err) {
    console.error(`Failed to read file "${filePath}": ${String(err)}`);
    process.exit(1);
  }

  const skipEnrichment = process.argv.includes("--no-enrich");

  processCSV(content, { skipEnrichment })
    .then((result) => {
      process.exit(result.errors.length > 0 ? 1 : 0);
    })
    .catch((err) => {
      console.error("Fatal error:", err);
      process.exit(1);
    });
}
