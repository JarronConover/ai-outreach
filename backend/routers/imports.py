from fastapi import APIRouter, HTTPException, UploadFile, File
from backend.db.client import get_db
from backend.services.csv_import import parse_companies_csv, parse_people_csv, parse_demos_csv
from backend.services.smart_import import smart_import_csv

router = APIRouter(tags=["imports"])

_PARSERS = {
    "companies": parse_companies_csv,
    "people":    parse_people_csv,
    "demos":     parse_demos_csv,
}

_UPSERT_CONFLICT: dict[str, str] = {
    "companies": "id",
    "people":    "email",
    "demos":     "id",
}


@router.post("/import/smart", status_code=200)
async def import_csv_smart(file: UploadFile = File(...)):
    """Upload any CSV — LLM auto-maps columns to companies and people."""
    content = (await file.read()).decode("utf-8", errors="replace")
    try:
        result = smart_import_csv(content)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return result


@router.post("/import/{table}", status_code=200)
async def import_csv(table: str, file: UploadFile = File(...)):
    """Upload a structured CSV export and upsert rows into Supabase.

    table must be one of: companies, people, demos
    Import order matters: companies → people → demos.
    """
    if table not in _PARSERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown table '{table}'. Must be: companies, people, demos",
        )
    content = (await file.read()).decode("utf-8", errors="replace")
    rows, errors = _PARSERS[table](content)

    if not rows:
        return {"table": table, "imported": 0, "errors": errors}

    try:
        db = get_db()
        db.table(table).upsert(rows, on_conflict=_UPSERT_CONFLICT[table]).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Supabase upsert failed: {exc}")

    return {"table": table, "imported": len(rows), "errors": errors}
