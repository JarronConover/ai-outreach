/**
 * Step 1 — CSV Parsing
 *
 * Accepts raw CSV content (string) and returns an array of plain objects
 * where every key is the original column header and every value is a string.
 * Uses PapaParse for maximum tolerance of messy real-world CSV files.
 */

import Papa from "papaparse";
import type { RawRow } from "./types.js";

export interface ParseResult {
  rows: RawRow[];
  headers: string[];
  errors: string[];
}

/**
 * Parse raw CSV content into an array of row objects.
 *
 * - Skips completely empty rows
 * - Trims whitespace from headers and values
 * - Preserves original column names (does NOT rename)
 */
export function parseCsv(content: string): ParseResult {
  const errors: string[] = [];

  const result = Papa.parse<RawRow>(content, {
    header: true,
    skipEmptyLines: "greedy", // skip rows where every field is empty
    transformHeader: (header: string) => header.trim(),
    transform: (value: string) => value.trim(),
  });

  if (result.errors.length > 0) {
    for (const err of result.errors) {
      errors.push(`Row ${err.row ?? "?"}: ${err.message}`);
    }
  }

  const rows = result.data as RawRow[];
  const headers = result.meta.fields ?? [];

  return { rows, headers, errors };
}
