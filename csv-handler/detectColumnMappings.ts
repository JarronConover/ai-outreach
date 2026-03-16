/**
 * Step 2 — Column Mapping Detection
 *
 * Sends CSV column headers, a sample of rows, and the database schemas
 * to Gemini. The LLM returns a JSON mapping of:
 *   { person: { <db_field>: "<csv_column>" }, company: { <db_field>: "<csv_column>" } }
 *
 * Only columns that clearly correspond to a known DB field are returned.
 * Fields with no obvious match are omitted (not invented).
 */

import { GoogleGenerativeAI, SchemaType } from "@google/generative-ai";
import type { RawRow, ColumnMapping } from "./types.js";
import type { FieldDef } from "./schema.js";
import { schemaToPromptText } from "./schema.js";

const SAMPLE_ROWS = 5; // rows sent to LLM for context

function buildPrompt(
  headers: string[],
  sampleRows: RawRow[],
  companiesSchema: FieldDef[],
  peopleSchema: FieldDef[],
): string {
  const headerList = headers.map((h) => `"${h}"`).join(", ");
  const sampleJson = JSON.stringify(sampleRows, null, 2);

  return `You are a data mapping assistant. Your job is to map CSV column headers to database fields.

## Database Schemas

${schemaToPromptText(companiesSchema, "companies")}

${schemaToPromptText(peopleSchema, "people")}

## CSV Column Headers
${headerList}

## Sample Rows
${sampleJson}

## Task
Analyse the column headers and sample values. Return a JSON object with two keys:
- "person": maps database field names (people table) to CSV column names
- "company": maps database field names (companies table) to CSV column names

Rules:
1. Only include a mapping when you are confident the column matches that field.
2. Use EXACT column names from the CSV (case-sensitive).
3. Only use field names that exist in the schemas above.
4. Do not guess — leave out fields that have no clear match.
5. A single CSV column may map to at most one field.

Return ONLY valid JSON, no commentary.`;
}

const RESPONSE_SCHEMA = {
  type: SchemaType.OBJECT,
  properties: {
    person: {
      type: SchemaType.OBJECT,
      description: "Maps people table fields to CSV column names",
      additionalProperties: { type: SchemaType.STRING },
    },
    company: {
      type: SchemaType.OBJECT,
      description: "Maps companies table fields to CSV column names",
      additionalProperties: { type: SchemaType.STRING },
    },
  },
  required: ["person", "company"],
};

export async function detectColumnMappings(
  headers: string[],
  rows: RawRow[],
  companiesSchema: FieldDef[],
  peopleSchema: FieldDef[],
  apiKey: string,
): Promise<ColumnMapping> {
  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({
    model: "gemini-2.0-flash",
    generationConfig: {
      responseMimeType: "application/json",
      responseSchema: RESPONSE_SCHEMA as Parameters<typeof model.generateContent>[0] extends never
        ? never
        : // @ts-expect-error SDK typing — responseSchema is supported at runtime
          typeof RESPONSE_SCHEMA,
    },
  });

  const sample = rows.slice(0, SAMPLE_ROWS);
  const prompt = buildPrompt(headers, sample, companiesSchema, peopleSchema);

  const result = await model.generateContent(prompt);
  const text = result.response.text();

  let mapping: ColumnMapping;
  try {
    mapping = JSON.parse(text) as ColumnMapping;
  } catch {
    throw new Error(`LLM returned invalid JSON for column mapping: ${text}`);
  }

  // Validate: only allow field names that exist in the schemas
  const validPersonFields = new Set(peopleSchema.map((f) => f.name));
  const validCompanyFields = new Set(companiesSchema.map((f) => f.name));

  const cleanPerson = Object.fromEntries(
    Object.entries(mapping.person ?? {}).filter(([field]) => validPersonFields.has(field)),
  ) as ColumnMapping["person"];

  const cleanCompany = Object.fromEntries(
    Object.entries(mapping.company ?? {}).filter(([field]) => validCompanyFields.has(field)),
  ) as ColumnMapping["company"];

  return { person: cleanPerson, company: cleanCompany };
}
