"""
Loads all agent modules via importlib to avoid namespace collisions.

All agents (prospect, outreach, orchestrator, inbox) live in their own
subdirectories and use bare imports like `from schemas.input import ICPInput`.
importlib isolation prevents those bare names from polluting each other.
"""
from __future__ import annotations

import os
import sys
import json
import importlib.util

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROSPECT_AGENT_DIR = os.path.join(_ROOT, "prospect-agent")
_INBOX_AGENT_DIR = os.path.join(_ROOT, "inbox-agent")
_ICP_CONFIG_PATH = os.path.join(_ROOT, "business", "icp_config.json")


def _import_from(path: str, module_name: str):
    """Load a Python file as a module without affecting sys.modules permanently."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Orchestrator agent
# ---------------------------------------------------------------------------

_orch_mod = _import_from(
    os.path.join(_ROOT, "orchestrator-agent", "agent", "orchestrator.py"),
    "orchestrator_agent.agent.orchestrator",
)
OrchestratorAgent = _orch_mod.OrchestratorAgent

_pipeline_input_mod = _import_from(
    os.path.join(_ROOT, "orchestrator-agent", "schemas", "input.py"),
    "orchestrator_agent.schemas.input",
)
PipelineInput = _pipeline_input_mod.PipelineInput

# ---------------------------------------------------------------------------
# Prospect agent (requires sys.modules swap to resolve bare imports)
# ---------------------------------------------------------------------------

_pa_input = _import_from(os.path.join(_PROSPECT_AGENT_DIR, "schemas", "input.py"), "_pa.schemas.input")
_pa_output = _import_from(os.path.join(_PROSPECT_AGENT_DIR, "schemas", "output.py"), "_pa.schemas.output")
_pa_tracer = _import_from(os.path.join(_PROSPECT_AGENT_DIR, "agent", "tracer.py"), "_pa.agent.tracer")
_pa_exceptions = _import_from(os.path.join(_PROSPECT_AGENT_DIR, "agent", "exceptions.py"), "_pa.agent.exceptions")
_pa_tools = _import_from(os.path.join(_PROSPECT_AGENT_DIR, "tools", "people_sheet.py"), "_pa.tools.people_sheet")

ICPInput = _pa_input.ICPInput
log_trace = _pa_tracer.log_trace
append_people = _pa_tools.append_people
filter_duplicates = _pa_tools.filter_duplicates
get_existing_people = _pa_tools.get_existing_people

_swap_keys = ["schemas.input", "schemas.output", "agent.tracer", "agent.exceptions"]
_saved_mods = {k: sys.modules.get(k) for k in _swap_keys}
try:
    sys.modules["schemas.input"] = _pa_input
    sys.modules["schemas.output"] = _pa_output
    sys.modules["agent.tracer"] = _pa_tracer
    sys.modules["agent.exceptions"] = _pa_exceptions
    _pa_orch = _import_from(
        os.path.join(_PROSPECT_AGENT_DIR, "agent", "orchestrator.py"),
        "_pa.agent.orchestrator",
    )
    ProspectingAgent = _pa_orch.ProspectingAgent
finally:
    for _k, _v in _saved_mods.items():
        if _v is None:
            sys.modules.pop(_k, None)
        else:
            sys.modules[_k] = _v


# ---------------------------------------------------------------------------
# Default ICP config — always reloads from disk so References page edits
# take effect immediately on the next prospect run.
# ---------------------------------------------------------------------------

def get_default_icp() -> "ICPInput":
    """Read icp_config.json fresh each call."""
    with open(_ICP_CONFIG_PATH, "r") as f:
        data = json.load(f)
    return ICPInput(**data)


# Backwards-compat alias — evaluated lazily via the function going forward
DEFAULT_ICP = get_default_icp()
