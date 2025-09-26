import json

from tools.custom_fields_workflow_tools import get_custom_fields_workflow_tools


def test_workflow_tools_load():
    tools = get_custom_fields_workflow_tools()
    names = {t.name for t in tools}
    assert "cfm_list_workflow_scripts" in names
    # spot check a couple
    assert "cfm_03_fetch_clio_session" in names
    assert "cfm_08_resequence_display_order" in names


def test_list_scripts_returns_json_like():
    tools = get_custom_fields_workflow_tools()
    list_tool = next(t for t in tools if t.name == "cfm_list_workflow_scripts")
    out = list_tool.run({"base_dir": "/home/sysadmin01/custom-fields-manager"})
    # Should parse as JSON
    data = json.loads(out)
    assert "base" in data and "scripts" in data
    assert isinstance(data["scripts"], list)