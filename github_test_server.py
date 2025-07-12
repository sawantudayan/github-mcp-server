"""
Unit Tests for GitHub MCP Server
Run these tests to validate the implementation
"""
import json
from unittest.mock import patch, MagicMock

import pytest

pytest_plugins = ["pytest_asyncio"]

# Default values
IMPORTS_SUCCESSFUL = None
IMPORT_ERROR = None

try:
    from github_mcp_server import (
        mcp,
        analyze_file_changes,
        get_pr_template,
        suggest_templates
    )

    IMPORTS_SUCCESSFUL = True

except Exception as e:
    IMPORTS_SUCCESSFUL = False
    IMPORT_ERROR = str(e)


class TestImplementation:
    """Test that the required functions are implemented."""

    def test_imports(self):
        """Test that all required functions can be imported."""
        assert IMPORTS_SUCCESSFUL, f"Failed to import required functions: {IMPORT_ERROR if not IMPORTS_SUCCESSFUL else ''}"
        assert mcp is not None, "FastMCP server instance not found"
        assert callable(analyze_file_changes), "analyze_file_changes should be a callable function"
        assert callable(get_pr_template), "get_pr_template should be a callable function"
        assert callable(suggest_templates), "suggest_templates should be a callable function"


@pytest.mark.skipif(not IMPORTS_SUCCESSFUL, reason="Imports failed")
class TestAnalyzeFileChanges:
    """Test the analyze_file_changes tool."""

    async def test_returns_json_string(self):
        """Test that analyze_file_changes returns a JSON string."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="")

            result = await analyze_file_changes()

            assert isinstance(result, str), "Should return a string"
            data = json.loads(result)
            assert isinstance(data, dict), "Should return a JSON object"

    async def test_includes_required_fields(self):
        """Test that the result includes expected fields."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout="M\tfile1.py\n", stderr="")

            result = await analyze_file_changes()
            data = json.loads(result)

            is_implemented = not ("error" in data and "Not implemented" in str(data.get("error", "")))
            if is_implemented:
                assert any(key in data for key in ["files_changed", "files", "changes", "diff"]), \
                    "Result should include file change information"
            else:
                assert isinstance(data, dict), "Should return a JSON object even if not implemented"

    async def test_output_limiting(self):
        """Test that large diffs are properly truncated."""
        with patch('subprocess.run') as mock_run:
            large_diff = "\n".join([f"+ line {i}" for i in range(1000)])

            mock_run.side_effect = [
                MagicMock(stdout="M\tfile1.py\n", stderr=""),
                MagicMock(stdout="1 file changed, 1000 insertions(+)", stderr=""),
                MagicMock(stdout=large_diff, stderr=""),
                MagicMock(stdout="abc123 Initial commit", stderr="")
            ]

            result = await analyze_file_changes(include_diff=True)
            data = json.loads(result)

            if "error" not in data or "Not implemented" not in str(data.get("error", "")):
                if "diff" in data and data["diff"] != "Diff not included (set include_diff=true to see full diff)":
                    diff_lines = data["diff"].split('\n')
                    assert len(diff_lines) < 600, "Large diffs should be truncated"

                    if "truncated" in data:
                        assert data["truncated"] == True, "Should indicate truncation"

                    assert "truncated" in data["diff"].lower() or "..." in data["diff"], \
                        "Should indicate diff was truncated"


@pytest.mark.skipif(not IMPORTS_SUCCESSFUL, reason="Imports failed")
class TestGetPRTemplates:
    """Test the get_pr_templates tool."""

    async def test_returns_json_string(self):
        """Test that get_pr_templates returns a JSON string."""
        result = await get_pr_template()

        assert isinstance(result, str), "Should return a string"
        data = json.loads(result)

        is_implemented = not ("error" in data and isinstance(data, dict))
        if is_implemented:
            assert isinstance(data, list), "Should return a JSON array of templates"
        else:
            assert isinstance(data, dict), "Should return a JSON object even if not implemented"

    async def test_returns_templates(self):
        """Test that templates are returned."""
        result = await get_pr_template()
        templates = json.loads(result)

        is_implemented = not ("error" in templates and isinstance(templates, dict))
        if is_implemented:
            assert len(templates) > 0, "Should return at least one template"
            for template in templates:
                assert isinstance(template, dict), "Each template should be a dictionary"
                assert any(key in template for key in ["filename", "name", "type", "id"]), \
                    "Templates should have an identifier"
        else:
            assert isinstance(templates, dict), "Should return structured error for starter code"


@pytest.mark.skipif(not IMPORTS_SUCCESSFUL, reason="Imports failed")
class TestSuggestTemplate:
    """Test the suggest_template tool."""

    async def test_returns_json_string(self):
        """Test that suggest_template returns a JSON string."""
        result = await suggest_templates(
            "Fixed a bug in the authentication system",
            "bug"
        )

        assert isinstance(result, str), "Should return a string"
        data = json.loads(result)
        assert isinstance(data, dict), "Should return a JSON object"

    async def test_suggestion_structure(self):
        """Test that the suggestion has expected structure."""
        result = await suggest_templates(
            "Added new feature for user management",
            "feature"
        )
        suggestion = json.loads(result)

        is_implemented = not ("error" in suggestion and "Not implemented" in str(suggestion.get("error", "")))
        if is_implemented:
            assert any(key in suggestion for key in ["template", "recommended_template", "suggestion"]), \
                "Should include a template recommendation"
        else:
            assert isinstance(suggestion, dict), "Should return structured error for starter code"


@pytest.mark.skipif(not IMPORTS_SUCCESSFUL, reason="Imports failed")
class TestToolRegistration:
    """Test that tools are properly registered with FastMCP."""

    def test_tools_have_decorators(self):
        assert hasattr(analyze_file_changes, '__name__'), "analyze_file_changes should be a proper function"
        assert hasattr(get_pr_template, '__name__'), "get_pr_template should be a proper function"
        assert hasattr(suggest_templates, '__name__'), "suggest_templates should be a proper function"


if __name__ == "__main__":
    if not IMPORTS_SUCCESSFUL:
        print(f"❌ Cannot run tests - imports failed: {IMPORT_ERROR}")
        print("\nMake sure you've:")
        print("1. Implemented all three tool functions")
        print("2. Decorated them with @mcp.tool()")
        print("3. Installed dependencies with: uv pip sync")
        exit(1)

    pytest.main([__file__, "-v"])
