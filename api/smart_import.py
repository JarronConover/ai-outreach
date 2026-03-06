"""
Smart CSV importer — accepts any CSV structure.

Uses Gemini to auto-map columns to the companies and people schemas,
extracts + normalizes + enriches records, then upserts to Supabase.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import uuid
from typing import Optional

import google.generativeai as genai

from api.db import get_db

# ---------------------------------------------------------------------------
# Schema definitions (must match Supabase migration exactly)
# ---------------------------------------------------------------------------

COMPANIES_SCHEMA: dict[str, str] = {
    "name":           "Company or organisation name [REQUIRED]",
    "address":        "Street address",
    "city":           "City",
    "state":          "US state abbreviation or full name",
    "zip":            "Postal / ZIP code",
    "phone":          "Main phone number",
    "website":        "Company website URL",
    "industry":       "Industry or vertical (e.g. Construction, SaaS, Healthcare)",
    "employee_count": "Approximate number of employees (integer only)",
}

PEOPLE_SCHEMA: dict[str, str] = {
    "name":              "Full name of the person [REQUIRED]",
    "email":             "Business email address (unique key)",
    "phone":             "Direct phone number",
    "linkedin":          "LinkedIn profile URL (https://linkedin.com/in/...)",
    "title":             "Job title / role (e.g. CTO, VP Engineering, Founder)",
    "stage":             "CRM stage — one of: prospect | contacted | demo_scheduled | demo_completed | pricing | onboarding | client | not_interested | churned",
    "last_response":     "Type of last response from this person (e.g. email, call)",
    "last_contact":      "Type of last outreach to this person (e.g. email, call)",
    "last_response_date":"ISO 8601 date of last response (YYYY-MM-DD)",
    "last_contact_date": "ISO 8601 date of last contact (YYYY-MM-DD)",
}

VALID_STAGES = {
    "prospect", "contacted", "demo_scheduled", "demo_completed",
    "pricing", "onboarding", "client", "not_interested", "churned",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _str(v: object) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _email(v: object) -> Optional[str]:
    s = _str(v)
    if not s:
        return None
    lower = s.lower()
    return lower if re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", lower) else None


def _phone(v: object) -> Optional[str]:
    s = _str(v)
    if not s:
        return None
    cleaned = re.sub(r"[^\d+\-().\s]", "", s).strip()
    return cleaned if len(re.sub(r"\D", "", cleaned)) >= 7 else None


def _url(v: object) -> Optional[str]:
    s = _str(v)
    if not s:
        return None
    if re.match(r"^https?://", s, re.I):
        return s
    if "." in s and " " not in s:
        return f"https://{s}"
    return None


def _iso_date(v: object) -> Optional[str]:
    s = _str(v)
    if not s:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    # Try parsing common US dates
    from datetime import datetime
    for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _int(v: object) -> Optional[int]:
    s = _str(v)
    if not s:
        return None
    try:
        return int(re.sub(r"[^0-9]", "", s))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Step 1 — Parse CSV
# ---------------------------------------------------------------------------

def parse_csv(content: str) -> tuple[list[dict[str, str]], list[str]]:
    """Return (rows, headers) from raw CSV content."""
    reader = csv.DictReader(io.StringIO(content))
    rows = []
    for row in reader:
        cleaned = {k.strip(): v.strip() for k, v in row.items() if k}
        # Skip completely empty rows
        if any(v for v in cleaned.values()):
            rows.append(cleaned)
    headers = list(reader.fieldnames or [])
    return rows, [h.strip() for h in headers if h]


# ---------------------------------------------------------------------------
# Step 2 — Detect column mappings via Gemini
# ---------------------------------------------------------------------------

def _schema_prompt_block(schema: dict[str, str], table: str) -> str:
    lines = "\n".join(f"  - {field}: {desc}" for field, desc in schema.items())
    return f"Table: {table}\n{lines}"


def detect_column_mappings(
    headers: list[str],
    sample_rows: list[dict[str, str]],
    api_key: str,
) -> dict[str, dict[str, str]]:
    """
    Ask Gemini which CSV column maps to which DB field.
    Returns { "person": { db_field: csv_col }, "company": { db_field: csv_col } }
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )

    header_list = ", ".join(f'"{h}"' for h in headers)
    sample_json = json.dumps(sample_rows[:5], indent=2)

    prompt = f"""You are a data mapping assistant. Map CSV columns to database fields.

## Database Schemas

{_schema_prompt_block(COMPANIES_SCHEMA, "companies")}

{_schema_prompt_block(PEOPLE_SCHEMA, "people")}

## CSV Column Headers
{header_list}

## Sample Rows
{sample_json}

## Task
Return a JSON object with exactly two keys:
- "person": maps people table field names to CSV column names
- "company": maps companies table field names to CSV column names

Rules:
1. Only include a mapping when you are confident.
2. Use EXACT CSV column names (case-sensitive).
3. Only use field names from the schemas above.
4. If unsure, omit the field — do NOT guess.
5. One CSV column may only map to one field.

Return ONLY valid JSON."""

    result = model.generate_content(prompt)
    text = result.text.strip()

    try:
        mapping = json.loads(text)
    except json.JSONDecodeError:
        # Try extracting JSON block from response
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            mapping = json.loads(match.group())
        else:
            return {"person": {}, "company": {}}

    # Validate — only keep fields that exist in the schemas
    valid_person = set(PEOPLE_SCHEMA.keys())
    valid_company = set(COMPANIES_SCHEMA.keys())

    clean_person = {
        field: col
        for field, col in (mapping.get("person") or {}).items()
        if field in valid_person
    }
    clean_company = {
        field: col
        for field, col in (mapping.get("company") or {}).items()
        if field in valid_company
    }

    return {"person": clean_person, "company": clean_company}


# ---------------------------------------------------------------------------
# Step 3+4 — Extract + normalize entities
# ---------------------------------------------------------------------------

def extract_and_normalize(
    rows: list[dict[str, str]],
    mapping: dict[str, dict[str, str]],
) -> list[dict[str, object]]:
    """Return list of { company: {...}, person: {...} } dicts."""
    person_map = mapping.get("person", {})
    company_map = mapping.get("company", {})
    results = []

    for row in rows:
        company: dict[str, object] = {}
        person: dict[str, object] = {}

        for field, col in company_map.items():
            raw = row.get(col)
            if field == "employee_count":
                val = _int(raw)
            elif field == "website":
                val = _url(raw)
            elif field == "phone":
                val = _phone(raw)
            else:
                val = _str(raw)
            if val is not None:
                company[field] = val

        for field, col in person_map.items():
            raw = row.get(col)
            if field == "email":
                val = _email(raw)
            elif field == "phone":
                val = _phone(raw)
            elif field == "linkedin":
                val = _url(raw)
            elif field in ("last_response_date", "last_contact_date"):
                val = _iso_date(raw)
            elif field == "stage":
                s = (_str(raw) or "prospect").lower().replace(" ", "_").replace("-", "_")
                val = s if s in VALID_STAGES else "prospect"
            else:
                val = _str(raw)
            if val is not None:
                person[field] = val

        has_company = bool(company.get("name"))
        has_person = bool(person.get("name") or person.get("email"))
        if not has_company and not has_person:
            continue

        results.append({"company": company, "person": person})

    return results


# ---------------------------------------------------------------------------
# Step 5 — Enrich via Gemini (batched)
# ---------------------------------------------------------------------------

def enrich_data(
    rows: list[dict[str, object]],
    api_key: str,
    batch_size: int = 15,
) -> list[dict[str, object]]:
    """Fill missing obvious fields using Gemini. Returns enriched rows."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        generation_config=genai.GenerationConfig(response_mime_type="application/json"),
    )

    enriched_all: list[dict[str, object]] = []

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        prompt = f"""You are a CRM data enrichment assistant. Fill in missing fields ONLY when context strongly implies the value.

## Schemas
{_schema_prompt_block(COMPANIES_SCHEMA, "companies")}
{_schema_prompt_block(PEOPLE_SCHEMA, "people")}

## Records
{json.dumps(batch, indent=2)}

## Task
Return a JSON array of exactly {len(batch)} objects (same order as input).
Each object has "company" and "person" keys.
- Add values for missing fields IF you are confident.
- Set to null if unsure — do NOT fabricate uncertain data.
- Do NOT modify existing field values.
- Only use fields from the schemas above.
- Preserve all existing values exactly."""

        try:
            result = model.generate_content(prompt)
            enriched_batch = json.loads(result.text)
            if not isinstance(enriched_batch, list) or len(enriched_batch) != len(batch):
                enriched_all.extend(batch)
                continue
            # Merge: original values win; LLM can only fill nulls
            for orig, llm in zip(batch, enriched_batch):
                merged_company = {
                    **{k: v for k, v in (llm.get("company") or {}).items() if v is not None},
                    **orig.get("company", {}),  # type: ignore[arg-type]
                }
                merged_person = {
                    **{k: v for k, v in (llm.get("person") or {}).items() if v is not None},
                    **orig.get("person", {}),  # type: ignore[arg-type]
                }
                enriched_all.append({"company": merged_company, "person": merged_person})
        except Exception:
            enriched_all.extend(batch)

    return enriched_all


# ---------------------------------------------------------------------------
# Step 6 — Upsert companies
# ---------------------------------------------------------------------------

def upsert_companies(
    rows: list[dict[str, object]],
) -> tuple[dict[str, str], list[str]]:
    """
    Upsert companies; returns (name_lower → id map, errors).
    """
    db = get_db()
    company_map: dict[str, str] = {}
    errors: list[str] = []

    seen: dict[str, dict[str, object]] = {}
    for row in rows:
        company = row.get("company") or {}
        name = _str(company.get("name"))  # type: ignore[arg-type]
        if name and name.lower() not in seen:
            seen[name.lower()] = company  # type: ignore[assignment]

    for key, company in seen.items():
        name = str(company["name"])
        try:
            res = db.table("companies").select("*").ilike("name", name).maybe_single().execute()
            existing = res.data

            if existing:
                patch = {
                    field: company[field]
                    for field in COMPANIES_SCHEMA
                    if field != "name"
                    and field in company
                    and not existing.get(field)
                }
                if patch:
                    db.table("companies").update(patch).eq("id", existing["id"]).execute()
                company_map[key] = existing["id"]
            else:
                new_id = str(uuid.uuid4())
                db.table("companies").insert({**company, "id": new_id}).execute()
                company_map[key] = new_id
        except Exception as exc:
            errors.append(f'Company "{name}": {exc}')

    return company_map, errors


# ---------------------------------------------------------------------------
# Step 7 — Upsert people
# ---------------------------------------------------------------------------

def upsert_people(
    rows: list[dict[str, object]],
    company_map: dict[str, str],
) -> tuple[int, list[str]]:
    """Upsert people; returns (count, errors)."""
    db = get_db()
    errors: list[str] = []
    upserted = 0

    seen: dict[str, tuple[dict[str, object], Optional[str]]] = {}
    for row in rows:
        person = row.get("person") or {}
        company = row.get("company") or {}
        if not person.get("name") and not person.get("email"):
            continue
        dedup_key = (
            f"email:{str(person['email']).lower()}"
            if person.get("email")
            else f"name:{str(person.get('name','')).lower()}:{str(company.get('name','')).lower()}"
        )
        if dedup_key not in seen:
            company_name = _str(company.get("name"))  # type: ignore[arg-type]
            seen[dedup_key] = (person, company_name)  # type: ignore[assignment]

    for _, (person, company_name) in seen.items():
        label = str(person.get("email") or person.get("name") or "(unknown)")
        company_id = company_map.get(company_name.lower()) if company_name else None

        try:
            existing = None

            if person.get("email"):
                res = db.table("people").select("*").eq("email", str(person["email"])).maybe_single().execute()
                existing = res.data

            if not existing and person.get("name") and company_id:
                res = (
                    db.table("people")
                    .select("*")
                    .ilike("name", str(person["name"]))
                    .eq("company_id", company_id)
                    .maybe_single()
                    .execute()
                )
                existing = res.data

            if existing:
                patch: dict[str, object] = {
                    field: person[field]
                    for field in PEOPLE_SCHEMA
                    if field in person and not existing.get(field)
                }
                if not existing.get("company_id") and company_id:
                    patch["company_id"] = company_id
                if patch:
                    db.table("people").update(patch).eq("id", existing["id"]).execute()
            else:
                payload: dict[str, object] = {**person}
                if company_id:
                    payload["company_id"] = company_id
                if not payload.get("stage"):
                    payload["stage"] = "prospect"
                payload["id"] = str(uuid.uuid4())
                db.table("people").insert(payload).execute()

            upserted += 1
        except Exception as exc:
            errors.append(f'Person "{label}": {exc}')

    return upserted, errors


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def smart_import_csv(
    content: str,
    skip_enrichment: bool = False,
) -> dict[str, object]:
    """
    Process any CSV: auto-map columns, extract companies + people, upsert to Supabase.

    Returns:
      { rows_read, companies_upserted, people_upserted, errors }
    """
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    errors: list[str] = []

    # 1. Parse
    rows, headers = parse_csv(content)
    if not rows:
        return {"rows_read": 0, "companies_upserted": 0, "people_upserted": 0, "errors": ["No rows found in CSV."]}

    # 2. Detect column mappings
    mapping = detect_column_mappings(headers, rows, api_key)
    if not mapping["person"] and not mapping["company"]:
        return {
            "rows_read": len(rows),
            "companies_upserted": 0,
            "people_upserted": 0,
            "errors": ["Could not map any CSV columns to known database fields."],
        }

    # 3+4. Extract + normalize
    extracted = extract_and_normalize(rows, mapping)

    # 5. Enrich
    if not skip_enrichment and api_key:
        extracted = enrich_data(extracted, api_key)

    # 6. Upsert companies
    company_map, company_errors = upsert_companies(extracted)
    errors.extend(company_errors)

    # 7. Upsert people
    people_count, people_errors = upsert_people(extracted, company_map)
    errors.extend(people_errors)

    return {
        "rows_read": len(rows),
        "companies_upserted": len(company_map),
        "people_upserted": people_count,
        "errors": errors,
    }
