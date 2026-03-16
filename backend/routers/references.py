"""
Endpoints for reading and writing business reference files:
  - templates (*.html, *.txt) in business/templates/
  - icp_config.json in business/
"""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/references", tags=["references"])

BUSINESS_DIR = Path(__file__).resolve().parents[2] / "business"
TEMPLATES_DIR = BUSINESS_DIR / "templates"
ICP_PATH = BUSINESS_DIR / "icp_config.json"

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

TEMPLATE_LABELS = {
    "prospect_outreach.html": "Prospect Outreach",
    "client_outreach.html": "Client Outreach",
    "followup_email.html": "Follow-Up Email",
    "demo_invite.html": "Demo Invite",
    "interested_reply.txt": "Interested Reply",
    "not_interested_reply.txt": "Not Interested Reply",
    "demo_request_reply.txt": "Demo Request Reply",
}


def _template_info(path: Path) -> dict:
    return {
        "name": path.name,
        "label": TEMPLATE_LABELS.get(path.name, path.stem.replace("_", " ").title()),
        "type": "html" if path.suffix == ".html" else "text",
    }


@router.get("/templates")
def list_templates():
    files = sorted(TEMPLATES_DIR.glob("*"), key=lambda p: p.name)
    return [_template_info(f) for f in files if f.is_file()]


@router.get("/templates/{name}")
def get_template(name: str):
    path = TEMPLATES_DIR / name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Template not found")
    return {**_template_info(path), "content": path.read_text(encoding="utf-8")}


class TemplateSave(BaseModel):
    content: str


@router.put("/templates/{name}")
def save_template(name: str, body: TemplateSave):
    path = TEMPLATES_DIR / name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Template not found")
    path.write_text(body.content, encoding="utf-8")
    return {"ok": True}


# ---------------------------------------------------------------------------
# ICP Config
# ---------------------------------------------------------------------------

@router.get("/icp")
def get_icp():
    if not ICP_PATH.exists():
        raise HTTPException(status_code=404, detail="icp_config.json not found")
    return json.loads(ICP_PATH.read_text(encoding="utf-8"))


class IcpSave(BaseModel):
    data: dict


@router.put("/icp")
def save_icp(body: IcpSave):
    ICP_PATH.write_text(json.dumps(body.data, indent=2), encoding="utf-8")
    return {"ok": True}
