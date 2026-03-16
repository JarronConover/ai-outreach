/**
 * Step 5 — Data Enrichment
 *
 * Sends batches of extracted rows to Gemini and asks it to fill in
 * missing fields ONLY when the context strongly implies the value.
 *
 * Rules enforced here and in the prompt:
 *  - Never fabricate uncertain data (return null if unsure)
 *  - Only use field names that exist in the DB schemas
 *  - Batch size: 15 rows per LLM call
 *
 * The LLM returns a JSON array of the same length as the input batch,
 * each item being the enriched { company, person } object.
 */

import { GoogleGenerativeAI, SchemaType } from "@google/generative-ai";
import type { ExtractedRow } from "./types.js";
import type { FieldDef } from "./schema.js";
import { schemaToPromptText } from "./schema.js";

const BATCH_SIZE = 15;

// ─── prompt ───────────────────────────────────────────────────────────────────

function buildEnrichPrompt(batch: ExtractedRow[], companiesSchema: FieldDef[], peopleSchema: FieldDef[]): string {
  return `You are a CRM data enrichment assistant. Fill in missing fields for the records below.

## Database Schemas

${schemaToPromptText(companiesSchema, "companies")}

${schemaToPromptText(peopleSchema, "people")}

## Records to Enrich
${JSON.stringify(batch, null, 2)}

## Task
For each record, examine the existing data and add values for any missing fields IF the data strongly implies the value.

Examples of acceptable enrichment:
- company "Acme Construction" → industry: "Construction"
- company "TechFlow SaaS" → industry: "Software"
- LinkedIn URL "linkedin.com/in/john.smith" → infer nothing extra (don't guess name/email)

Rules:
1. Return ONLY fields that exist in the schemas above.
2. If you are unsure, set the value to null — do NOT guess.
3. Do NOT modify fields that already have a value.
4. Return a JSON array of exactly ${batch.length} objects, each with "company" and "person" keys.
5. Preserve all existing field values exactly as given.`;
}

// Response schema: array of ExtractedRow-shaped objects
const RESPONSE_SCHEMA = {
  type: SchemaType.ARRAY,
  items: {
    type: SchemaType.OBJECT,
    properties: {
      company: {
        type: SchemaType.OBJECT,
        description: "Company fields",
        additionalProperties: true,
      },
      person: {
        type: SchemaType.OBJECT,
        description: "Person fields",
        additionalProperties: true,
      },
    },
    required: ["company", "person"],
  },
};

// ─── enrichment ───────────────────────────────────────────────────────────────

async function enrichBatch(
  batch: ExtractedRow[],
  companiesSchema: FieldDef[],
  peopleSchema: FieldDef[],
  model: ReturnType<InstanceType<typeof GoogleGenerativeAI>["getGenerativeModel"]>,
): Promise<ExtractedRow[]> {
  const prompt = buildEnrichPrompt(batch, companiesSchema, peopleSchema);
  const result = await model.generateContent(prompt);
  const text = result.response.text();

  let enriched: ExtractedRow[];
  try {
    enriched = JSON.parse(text) as ExtractedRow[];
  } catch {
    console.warn("LLM returned invalid JSON during enrichment — using original batch.");
    return batch;
  }

  if (!Array.isArray(enriched) || enriched.length !== batch.length) {
    console.warn("LLM enrichment response length mismatch — using original batch.");
    return batch;
  }

  // Merge: keep original values, layer in non-null LLM additions
  return batch.map((original, i) => {
    const llm = enriched[i] ?? {};
    const mergedCompany = Object.fromEntries([
      ...Object.entries(llm.company ?? {}),
      ...Object.entries(original.company), // original wins
    ]);
    const mergedPerson = Object.fromEntries([
      ...Object.entries(llm.person ?? {}),
      ...Object.entries(original.person), // original wins
    ]);

    // Drop null values introduced by LLM
    const cleanCompany = Object.fromEntries(Object.entries(mergedCompany).filter(([, v]) => v !== null));
    const cleanPerson = Object.fromEntries(Object.entries(mergedPerson).filter(([, v]) => v !== null));

    return { company: cleanCompany, person: cleanPerson } as ExtractedRow;
  });
}

/**
 * Enrich all rows in batches of BATCH_SIZE.
 * Failures in a batch are caught and the original rows are returned for that batch.
 */
export async function enrichData(
  rows: ExtractedRow[],
  companiesSchema: FieldDef[],
  peopleSchema: FieldDef[],
  apiKey: string,
): Promise<ExtractedRow[]> {
  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({
    model: "gemini-2.0-flash",
    generationConfig: {
      responseMimeType: "application/json",
    },
  });

  const results: ExtractedRow[] = [];

  for (let i = 0; i < rows.length; i += BATCH_SIZE) {
    const batch = rows.slice(i, i + BATCH_SIZE);
    try {
      const enriched = await enrichBatch(batch, companiesSchema, peopleSchema, model);
      results.push(...enriched);
    } catch (err) {
      console.warn(`Enrichment batch ${i}–${i + batch.length} failed: ${String(err)} — using originals.`);
      results.push(...batch);
    }
  }

  return results;
}
