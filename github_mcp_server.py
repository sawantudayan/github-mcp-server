"""
Minimal MCP Server that provides tools for analyzing file changes and suggesting PR Templates
"""
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastMCP Server
mcp = FastMCP("github-mcp-server")

# PR Templates directory (shared across all modules)
# TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

TEMPLATES_DIR = Path(os.getenv("GITHUB_MCP_TEMPLATES_DIR")) if os.getenv("GITHUB_MCP_TEMPLATES_DIR") else Path(
    __file__).parent / "templates"
print(TEMPLATES_DIR)

# Default PT Templates
DEFAULT_TEMPLATES = {
    "bug.md": "Bug Fix",
    "feature.md": "Feature",
    "docs.md": "Documentation",
    "refactor.md": "Refactor",
    "test.md": "Test",
    "performance.md": "Performance",
    "security.md": "Security"
}

# Type mapping for PR templates
TYPE_MAPPING = {
    "bug": "bug.md",
    "fix": "bug.md",
    "feature": "feature.md",
    "enhancement": "feature.md",
    "docs": "docs.md",
    "documentation": "docs.md",
    "refactor": "refactor.md",
    "cleanup": "refactor.md",
    "test": "test.md",
    "testing": "test.md",
    "performance": "performance.md",
    "optimization": "performance.md",
    "security": "security.md"
}

"""
Future Improvements
- Add pagination for extremely large diffs
- Return language-level diff summaries (e.g., how many functions modified)
- Stream this data to Claude progressively via chunking
"""


@mcp.tool()
async def analyze_file_changes(
        base_branch: str = "master",
        include_diff: bool = True,
        max_diff_lines: int = 500,
        working_directory: Optional[str] = None
):
    try:
        if working_directory is None:
            try:
                context = mcp.get_context()
                roots_result = await context.session.list_roots()
                root = roots_result.roots[0]
                working_directory = root.uri.path
            except Exception:
                pass  # fallback to os.getcwd()

        cwd = working_directory if working_directory else os.getcwd()

        debug_info = {
            "provided_working_directory": working_directory,
            "actual_cwd": cwd,
            "server_process_cwd": os.getcwd(),
            "server_file_location": str(Path(__file__).parent),
            "roots_check": None
        }

        # roots debug again (redundant, but safe for tracing)
        try:
            context = mcp.get_context()
            roots_result = await context.session.list_roots()
            debug_info["roots_check"] = {
                "found": True,
                "count": len(roots_result.roots),
                "roots": [str(root.uri) for root in roots_result.roots]
            }
        except Exception as e:
            debug_info["roots_check"] = {
                "found": False,
                "error": str(e)
            }

        # --name-status gives file change summary
        files_result = subprocess.run(
            ["git", "diff", "--name-status", f"{base_branch}...HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd
        )

        files_changed = []
        for line in files_result.stdout.strip().split('\n'):
            if line:
                parts = line.strip().split('\t')
                if len(parts) == 2:
                    status, filename = parts
                    files_changed.append({"status": status, "file": filename})

        # --stat output
        stat_result = subprocess.run(
            ["git", "diff", "--stat", f"{base_branch}...HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd
        )

        diff_content = ""
        truncated = False
        diff_lines = []

        if include_diff:
            diff_result = subprocess.run(
                ["git", "diff", f"{base_branch}...HEAD"],
                capture_output=True,
                text=True,
                cwd=cwd
            )
            diff_lines = diff_result.stdout.split('\n')

            if len(diff_lines) > max_diff_lines:
                diff_content = '\n'.join(diff_lines[:max_diff_lines])
                diff_content += f"\n\n... Output truncated. Showing {max_diff_lines} of {len(diff_lines)} lines ..."
                diff_content += "\n... Use max_diff_lines parameter to see more ..."
                truncated = True
            else:
                diff_content = diff_result.stdout

        commits_result = subprocess.run(
            ["git", "log", "--oneline", f"{base_branch}...HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd
        )

        analysis = {
            "base_branch": base_branch,
            "files_changed": files_changed,
            "statistics": stat_result.stdout,
            "commits": commits_result.stdout,
            "diff": diff_content if include_diff else "Diff not included (set include_diff=true to see full diff)",
            "truncated": truncated,
            "total_diff_lines": len(diff_lines) if include_diff else 0,
            "_debug": debug_info
        }

        # return json.dumps(analysis, indent=2)
        return {"result": json.dumps(analysis)}

    except subprocess.CalledProcessError as e:
        return json.dumps({"error": f"Git Error: {e.stderr}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


"""
Future Improvements 
- Dynamic scanning of template directories (instead of hardcoded DEFAULT_TEMPLATES)
- Sorting or prioritizing templates
- Allowing Claude to create new templates dynamically 
"""


@mcp.tool()
async def get_pr_template() -> dict:
    """
    List PR templates from directory with their content.

    Returns:
        JSON list of templates with filename, type, and file content.
        If a template file is missing or unreadable, an error message is included as content.
    """
    templates = []

    for filename, template_type in DEFAULT_TEMPLATES.items():
        template_path = TEMPLATES_DIR / filename
        try:
            content = template_path.read_text()
        except Exception as e:
            content = f"Error loading template '{filename}': {str(e)}"

        templates.append({
            "filename": filename,
            "type": template_type,
            "content": content
        })

    # Return as dict, not plain string
    return {"result": json.dumps(templates)}


"""
Future Improvements
- Add keywords per template for semantic suggestions
- Use Claude to classify changes_summary dynamically (instead of needing change_type)
- Introduce confidence scoring based on token overlap or similarity between changes_summary and template_content 
"""


@mcp.tool()
async def suggest_templates(
        changes_summary: str,
        change_type: str
) -> str:
    """
    Let Claude analyze the changes and suggest the most appropriate PR template,
    with alternatives in case of uncertainty.

    Args:
        changes_summary: Analysis of what the changes do
        change_type: Identified type of change (e.g., bug, feature, docs)

    Returns:
        JSON object containing recommended template, alternatives, and reasoning
    """
    # Fetch available templates
    templates_response = await get_pr_template()
    templates = json.loads(templates_response)

    # Normalize and lookup the main template file
    normalized_type = change_type.lower().strip()
    template_file = TYPE_MAPPING.get(normalized_type, "feature.md")

    # Identify recommended template
    selected_template = next(
        (t for t in templates if t["filename"] == template_file),
        templates[0]  # fallback
    )

    # Build a list of alternatives (excluding selected)
    alternatives = [t for t in templates if t["filename"] != selected_template["filename"]][:3]  # Limit to top 3 others

    suggestion = {
        "recommended_template": selected_template,
        "alternatives": alternatives,
        "confidence_level": "high" if normalized_type in TYPE_MAPPING else "medium",
        "reasoning": (
            f"Based on your analysis: '{changes_summary}', this appears to be a "
            f"{change_type} change. The mapping matched '{template_file}'."
        ),
        "template_content": selected_template["content"],
        "usage_hint": ("Claude can help fill out this template or explore alternatives if needed.")
    }

    # return json.dumps(suggestion, indent=2)
    return {
        "result": json.dumps(suggestion)  # keep it compact, no indent needed
    }


if __name__ == "__main__":
    mcp.run()
