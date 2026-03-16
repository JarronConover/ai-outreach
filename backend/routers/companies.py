from fastapi import APIRouter, HTTPException
from backend.db.crud import get_companies, delete_company

router = APIRouter(tags=["companies"])


@router.get("/companies")
def list_companies():
    """Return all companies from Supabase."""
    try:
        return get_companies()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/companies/{company_id}", status_code=204)
def delete_company_endpoint(company_id: str):
    """Delete a company by ID."""
    try:
        delete_company(company_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
