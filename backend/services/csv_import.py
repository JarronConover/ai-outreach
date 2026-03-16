"""
CSV parsing utilities for Google Sheets exports → Supabase rows.

Expected column headers (case-insensitive) match the sheet config:
  Companies: id, name, address, city, state, zip, phone, website, industry, employee_count
  People:    id, name, company_id, email, phone, linkedin, title, stage,
             last_demo_id, next_demo_id, last_response, last_contact,
             last_response_date, last_contact_date
  Demos:     id, people_id, company_id, type, date, status, count, event_id
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime
from typing import Optional


_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y",
    "%m/%d/%y %H:%M:%S",
    "%m/%d/%y %H:%M",
    "%m/%d/%y",
)


def _parse_dt(raw: str) -> Optional[str]:
    raw = raw.strip()
    if not raw:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).isoformat()
        except ValueError:
            continue
    return None


def _uuid(raw: str) -> str:
    raw = raw.strip()
    if raw:
        try:
            uuid.UUID(raw)
            return raw
        except ValueError:
            pass
    return str(uuid.uuid4())


def _str(raw: str) -> Optional[str]:
    v = raw.strip()
    return v if v else None


def _int(raw: str) -> Optional[int]:
    raw = raw.strip().replace(",", "")
    try:
        return int(raw) if raw else None
    except ValueError:
        return None


def _norm(row: dict) -> dict:
    return {k.lower().strip(): v for k, v in row.items()}


def parse_companies_csv(content: str) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    errors: list[str] = []
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    for i, raw_row in enumerate(reader, start=2):
        row = _norm(raw_row)
        name = _str(row.get("name", ""))
        if not name:
            errors.append(f"Row {i}: skipped — missing 'name'")
            continue
        try:
            rows.append({
                "id":             _uuid(row.get("id", "")),
                "name":           name,
                "address":        _str(row.get("address", "")),
                "city":           _str(row.get("city", "")),
                "state":          _str(row.get("state", "")),
                "zip":            _str(row.get("zip", "")),
                "phone":          _str(row.get("phone", "")),
                "website":        _str(row.get("website", "")),
                "industry":       _str(row.get("industry", "")),
                "employee_count": _int(row.get("employee_count", "")),
            })
        except Exception as exc:
            errors.append(f"Row {i}: {exc}")
    return rows, errors


def parse_people_csv(content: str) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    errors: list[str] = []
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    for i, raw_row in enumerate(reader, start=2):
        row = _norm(raw_row)
        email = _str(row.get("email", ""))
        name = _str(row.get("name", ""))
        if not email:
            errors.append(f"Row {i}: skipped — missing 'email'")
            continue
        if not name:
            errors.append(f"Row {i}: skipped — missing 'name'")
            continue
        try:
            rows.append({
                "id":                 _uuid(row.get("id", "")),
                "name":               name,
                "company_id":         _uuid(row.get("company_id", "")) if row.get("company_id", "").strip() else None,
                "email":              email,
                "phone":              _str(row.get("phone", "")),
                "linkedin":           _str(row.get("linkedin", row.get("linkedin_url", ""))),
                "title":              _str(row.get("title", "")),
                "stage":              _str(row.get("stage", "")) or "prospect",
                "last_response":      _str(row.get("last_response", "")),
                "last_contact":       _str(row.get("last_contact", "")),
                "last_response_date": _parse_dt(row.get("last_response_date", "")),
                "last_contact_date":  _parse_dt(row.get("last_contact_date", "")),
            })
        except Exception as exc:
            errors.append(f"Row {i}: {exc}")
    return rows, errors


def parse_demos_csv(content: str) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    errors: list[str] = []
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    for i, raw_row in enumerate(reader, start=2):
        row = _norm(raw_row)
        people_id = _str(row.get("people_id", ""))
        if not people_id:
            errors.append(f"Row {i}: skipped — missing 'people_id'")
            continue
        try:
            rows.append({
                "id":         _uuid(row.get("id", "")),
                "people_id":  _uuid(people_id),
                "company_id": _uuid(row.get("company_id", "")) if row.get("company_id", "").strip() else None,
                "type":       _str(row.get("type", "")) or "discovery",
                "date":       _parse_dt(row.get("date", "")),
                "status":     _str(row.get("status", "")) or "scheduled",
                "count":      _int(row.get("count", "")),
                "event_id":   _str(row.get("event_id", "")),
            })
        except Exception as exc:
            errors.append(f"Row {i}: {exc}")
    return rows, errors
