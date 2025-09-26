"""
LangChain tools that wrap numbered workflow scripts in ~/custom-fields-manager.

Each tool will attempt to locate the script by filename in common locations:
  - ~/custom-fields-manager/scripts
  - ~/custom-fields-manager/workflow
  - ~/custom-fields-manager (repo root)

If a script is missing, the tool returns a structured error instead of failing.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from loguru import logger
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool


CFM_DEFAULT_PATH = "/home/sysadmin01/custom-fields-manager"


@dataclass
class ScriptSpec:
    tool_name: str
    filename: str
    description: str


SCRIPT_SPECS: List[ScriptSpec] = [
    # Phase 1: Audit & Discovery
    ScriptSpec("cfm_01_check_missing_fields", "01_check_missing_fields.py", "Audit: Check for missing custom fields vs. expected baseline."),
    ScriptSpec("cfm_02_field_checker", "02_field_checker.py", "Audit: Deep field checker for inconsistencies and anomalies."),

    # Phase 2: Authentication
    ScriptSpec("cfm_03_fetch_clio_session", "03_fetch_clio_session.py", "Authentication: Fetch Clio session cookie/CSRF for web workflows."),

    # Phase 3: Field Creation
    ScriptSpec("cfm_04_create_custom_fields", "04_create_custom_fields.py", "Create: Create a batch of standard custom fields from a spec."),
    ScriptSpec("cfm_05_create_missing_fields", "05_create_missing_fields.py", "Create: Create only missing fields identified by audit."),
    ScriptSpec("cfm_06_update_essential_fields", "06_update_essential_fields.py", "Create: Update essential fields with required properties."),

    # Phase 4: Field Organization
    ScriptSpec("cfm_07_batch_update_fields", "07_batch_update_fields.py", "Organize: Batch update properties across many fields."),
    ScriptSpec("cfm_08_resequence_display_order", "08_resequence_display_order.py", "Organize: Resequence display order for fields."),
    ScriptSpec("cfm_09_assign_fields_to_set", "09_assign_fields_to_set.py", "Organize: Assign fields to the appropriate field set."),

    # Phase 5: Verification & Reporting
    ScriptSpec("cfm_10_verify_field_orders", "10_verify_field_orders.py", "Verify: Confirm field ordering is correct across entities."),
    ScriptSpec("cfm_11_verify_field_assignment", "11_verify_field_assignment.py", "Verify: Ensure fields are assigned to the expected sets."),
    ScriptSpec("cfm_12_generate_migration_dashboard", "12_generate_migration_dashboard.py", "Report: Generate migration dashboard/report."),

    # Specialized Workflows
    ScriptSpec("cfm_20_complete_essential_data_setup", "20_complete_essential_data_setup.py", "Workflow: Complete setup for essential data set."),
    ScriptSpec("cfm_21_complete_workers_comp_setup", "21_complete_workers_comp_setup.py", "Workflow: Complete Workers' Comp specific setup."),
]


def _resolve_script_path(filename: str, base: Optional[str] = None) -> Optional[Path]:
    """Try to resolve a workflow script path in known locations."""
    base_dir = Path(base or CFM_DEFAULT_PATH).expanduser()
    candidates = [
        base_dir / "scripts" / filename,
        base_dir / "workflow" / filename,
        base_dir / filename,
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


class WorkflowArgs(BaseModel):
    """Generic args schema for workflow script tools."""
    extra_args: Optional[str] = Field(
        default=None,
        description="Optional extra arguments to pass to the script (raw string parsed with shell-style splitting).",
    )
    working_dir: Optional[str] = Field(
        default=None,
        description="Optional working directory to run the script from (defaults to the custom-fields-manager root).",
    )


def _run_script(script_path: Path, extra_args: Optional[str], cwd: Optional[Path]) -> Tuple[bool, str, str, int]:
    args_list: List[str] = ["python", str(script_path)]
    if extra_args:
        # Use shlex to safely split a user-provided arg string
        args_list.extend(shlex.split(extra_args))

    run_cwd = str(cwd or script_path.parent)
    logger.debug(f"Running workflow script: {' '.join(args_list)} (cwd={run_cwd})")

    try:
        proc = subprocess.run(
            args_list,
            cwd=run_cwd,
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minutes for long workflows
        )
        return (proc.returncode == 0, proc.stdout, proc.stderr, proc.returncode)
    except subprocess.TimeoutExpired:
        return (False, "", "Script timed out after 1800 seconds", -1)
    except Exception as e:
        return (False, "", str(e), -1)


def _make_tool(spec: ScriptSpec) -> StructuredTool:
    def _tool_impl(extra_args: Optional[str] = None, working_dir: Optional[str] = None) -> str:
        base_dir = Path(working_dir) if working_dir else Path(CFM_DEFAULT_PATH)
        script_path = _resolve_script_path(spec.filename, str(base_dir))
        if not script_path:
            return (
                f"{{\n  \"success\": false,\n  \"error\": \"Script not found: {spec.filename}\",\n"
                f"  \"searched_in\": [\"{base_dir}/scripts\", \"{base_dir}/workflow\", \"{base_dir}\"]\n}}"
            )

        ok, out, err, code = _run_script(script_path, extra_args, base_dir)
        return (
            "{\n"
            f"  \"success\": {str(ok).lower()},\n"
            f"  \"return_code\": {code},\n"
            f"  \"stdout\": {json_escape(out)},\n"
            f"  \"stderr\": {json_escape(err)}\n"
            "}"
        )

    return StructuredTool(
        name=spec.tool_name,
        description=spec.description + " Accepts extra_args for script flags.",
        func=_tool_impl,
        args_schema=WorkflowArgs,
    )


def json_escape(s: str) -> str:
    # Minimal JSON string escaper to avoid importing json for dumps, keeping outputs compact
    if s is None:
        return 'null'
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'


class ListScriptsArgs(BaseModel):
    base_dir: Optional[str] = Field(
        default=None,
        description="Override base directory for custom-fields-manager (defaults to ~/custom-fields-manager).",
    )


def _list_scripts(base_dir: Optional[str] = None) -> str:
    root = Path(base_dir or CFM_DEFAULT_PATH).expanduser()
    found = []
    for spec in SCRIPT_SPECS:
        p = _resolve_script_path(spec.filename, str(root))
        found.append({
            "tool": spec.tool_name,
            "filename": spec.filename,
            "path": str(p) if p else None,
            "exists": bool(p),
        })
    # Render inline JSON (avoid import json to keep outputs consistent with the other helper)
    def _esc(v: Optional[str]) -> str:
        return json_escape(v) if v is not None else 'null'
    items = []
    for it in found:
        items.append(
            "{"
            f"\"tool\": \"{it['tool']}\", "
            f"\"filename\": \"{it['filename']}\", "
            f"\"path\": {_esc(it['path'])}, "
            f"\"exists\": {str(it['exists']).lower()}"
            "}"
        )
    return "{" + f"\n  \"base\": \"{str(root)}\",\n  \"scripts\": [\n    " + ",\n    ".join(items) + "\n  ]\n}"


def get_custom_fields_workflow_tools() -> List[StructuredTool]:
    tools: List[StructuredTool] = []
    # Add lister tool first
    def _list_impl(base_dir: Optional[str] = None) -> str:
        return _list_scripts(base_dir)

    list_tool = StructuredTool(
        name="cfm_list_workflow_scripts",
        description="List known custom-fields-manager workflow scripts and whether they're present on disk.",
        func=_list_impl,
        args_schema=ListScriptsArgs,
    )
    tools.append(list_tool)

    for spec in SCRIPT_SPECS:
        tools.append(_make_tool(spec))

    return tools
