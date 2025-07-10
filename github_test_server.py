"""
Unit Tests for GitHub MCP Server
Run these tests to validate the implementation
"""
import pytest

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
        assert callable(get_pr_template), "get_pr_templates should be a callable function"
        assert callable(suggest_templates), "suggest_template should be a callable function"


if __name__ == "__main__":
    if not IMPORTS_SUCCESSFUL:
        print(f"❌ Cannot run tests - imports failed: {IMPORT_ERROR}")
        print("\nMake sure you've:")
        print("1. Implemented all three tool functions")
        print("2. Decorated them with @mcp.tool()")
        print("3. Installed dependencies with: uv sync")
        exit(1)

    # Run tests
    pytest.main([__file__, "-v"])
