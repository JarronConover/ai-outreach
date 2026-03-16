from fastapi import APIRouter, HTTPException
from backend.db.crud import get_people, delete_person

router = APIRouter(tags=["people"])


@router.get("/people")
def list_people():
    """List all people from Supabase with company_name resolved via join."""
    try:
        return get_people()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/people/{person_id}", status_code=204)
def delete_person_endpoint(person_id: str):
    """Delete a person by ID."""
    try:
        delete_person(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
