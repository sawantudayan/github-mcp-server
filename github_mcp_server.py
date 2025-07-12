"""
Minimal MCP Server that provides tools for analyzing file changes and suggesting PR Templates
"""
import json
import logging
import os
import re
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

TEMPLATE_KEYWORDS = {
    "bug.md": {"bug", "fix", "error", "issue", "crash", "fault"},
    "feature.md": {"feature", "enhancement", "add", "new", "implement", "upgrade"},
    "docs.md": {"docs", "documentation", "readme", "guide", "manual", "instructions"},
    "refactor.md": {"refactor", "cleanup", "restructure", "optimize", "simplify"},
    "test.md": {"test", "coverage", "unittest", "integration", "assert"},
    "performance.md": {"performance", "optimize", "speed", "benchmark", "improve"},
    "security.md": {"security", "vulnerability", "exploit", "safe", "penetration"},
}


def tokenize(text: str):
    """Simple tokenizer splitting on non-alphanumeric, lowercase tokens."""
    return re.findall(r'\b\w+\b', text.lower())


def compute_token_overlap_score(text_tokens, keywords):
    """Compute simple overlap score as ratio of keyword tokens found in text."""
    if not keywords:
        return 0.0
    text_token_counts = Counter(text_tokens)
    matched = sum(min(text_token_counts[k], 1) for k in keywords)
    return matched / len(keywords)


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
        page: int = 1,
        page_size: int = 100,
        working_directory: Optional[str] = None
):
    """
    Analyze git file changes with support for pagination, language-level summaries,
    and streaming data to Claude progressively.

    Args:
        base_branch: Branch to diff against (default 'master')
        include_diff: Whether to include diff content in response
        max_diff_lines: Max total diff lines to fetch and paginate through
        page: Page number for paginated diff output (1-based)
        page_size: Number of diff lines per page
        working_directory: Optional path to repo root

    Returns:
        JSON with files changed, stats, commits, paginated diff, language summary,
        and debug info.
    """
    try:
        if working_directory is None:
            try:
                context = mcp.get_context()
                roots_result = await context.session.list_roots()
                root = roots_result.roots[0]
                working_directory = root.uri.path
            except Exception:
                pass

        cwd = working_directory if working_directory else os.getcwd()

        debug_info = {
            "provided_working_directory": working_directory,
            "actual_cwd": cwd,
            "server_process_cwd": os.getcwd(),
            "server_file_location": str(Path(__file__).parent),
            "roots_check": None
        }

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
            all_diff_lines = diff_result.stdout.split('\n')

            # Pagination logic
            total_lines = len(all_diff_lines)
            start_line = (page - 1) * page_size
            end_line = start_line + page_size
            paged_diff_lines = all_diff_lines[start_line:end_line]

            diff_content = '\n'.join(paged_diff_lines)

            if end_line < total_lines:
                diff_content += f"\n\n... Page {page} of {((total_lines - 1) // page_size) + 1} ... Use page param to see more ..."

            if total_lines > max_diff_lines:
                truncated = True
                diff_content += f"\n\n... Total diff lines exceed max_diff_lines ({max_diff_lines}), output truncated."

            diff_lines = paged_diff_lines

        commits_result = subprocess.run(
            ["git", "log", "--oneline", f"{base_branch}...HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd
        )

        # Language-level diff summaries: count functions modified (basic heuristic)
        lang_function_counts = {}

        # Simple regex patterns for function definitions by language
        lang_patterns = {
            "python": re.compile(r'^\+.*def\s+\w+\('),
            "javascript": re.compile(r'^\+.*function\s+\w+\('),
            "typescript": re.compile(r'^\+.*function\s+\w+\('),
            "java": re.compile(r'^\+.*(public|private|protected)\s+\w+\s+\w+\('),
            "csharp": re.compile(r'^\+.*(public|private|protected)\s+\w+\s+\w+\('),
            "go": re.compile(r'^\+.*func\s+\w+\('),
            # Add more languages/patterns as needed
        }

        for line in diff_lines:
            for lang, pattern in lang_patterns.items():
                if pattern.match(line):
                    lang_function_counts[lang] = lang_function_counts.get(lang, 0) + 1

        # Example streaming data chunking logic (pseudo-code/comment)
        # for chunk in chunkify(all_diff_lines, chunk_size=100):
        #     await claude_client.send(chunk)
        #     # Could await a response or just stream progressively
        #     # For now, just a placeholder comment here

        analysis = {
            "base_branch": base_branch,
            "files_changed": files_changed,
            "statistics": stat_result.stdout,
            "commits": commits_result.stdout,
            "diff": diff_content if include_diff else "Diff not included (set include_diff=true to see full diff)",
            "diff_page": page,
            "diff_page_size": page_size,
            "truncated": truncated,
            "total_diff_lines": len(all_diff_lines) if include_diff else 0,
            "language_function_modifications": lang_function_counts,
            "_debug": debug_info
        }

        return {"result": json.dumps(analysis)}

    except subprocess.CalledProcessError as e:
        return {"error": f"Git Error: {e.stderr}"}
    except Exception as e:
        return {"error": str(e)}


"""
Improvements v1.0
- Dynamic scanning of template directories (instead of hardcoded DEFAULT_TEMPLATES)
- Sorting or prioritizing templates
- Allowing Claude to create new templates dynamically 
"""


@mcp.tool()
async def get_pr_template() -> dict:
    """
    List PR templates dynamically from the templates directory, read their content,
    sort them alphabetically, and optionally allow Claude to add new templates dynamically.

    Returns:
        JSON list of templates with filename, type (derived), and file content.
        If a template file is missing or unreadable, an error message is included as content.
    """
    templates = []

    md_files = sorted(TEMPLATES_DIR.glob("*.md"), key=lambda p: p.name.lower())

    def derive_type(filename: str) -> str:
        # Remove extension, replace underscores with spaces, capitalize words
        base = filename.lower().replace(".md", "").replace("_", " ")
        # Map to friendly names or fallback
        type_map = {
            "bug": "Bug Fix",
            "feature": "Feature",
            "docs": "Documentation",
            "refactor": "Refactor",
            "test": "Test",
            "performance": "Performance",
            "security": "Security"
        }
        for key, friendly in type_map.items():
            if key in base:
                return friendly
        # Fallback: Title Case filename without extension
        return base.title()

    for path in md_files:
        filename = path.name
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            content = f"Error loading template '{filename}': {str(e)}"
        template_type = derive_type(filename)
        templates.append({
            "filename": filename,
            "type": template_type,
            "content": content
        })
    return {"result": json.dumps(templates)}


"""
Improvements v1.0 - 
- Added keywords per template for semantic suggestions
- Used Claude to classify changes_summary dynamically (instead of needing change_type)
- Introduced confidence scoring based on token overlap or similarity between changes_summary and template_content 
"""


@mcp.tool()
async def suggest_templates(changes_summary: str, change_type: str = None) -> str:
    """
    Suggest PR template based on semantic similarity and optionally dynamic classification by Claude.

    Args:
        changes_summary: Description of what changes accomplish
        change_type: Optional, existing label of change type (bug, feature, docs, etc.)

    Returns:
        JSON string with recommended template, alternatives, confidence, reasoning
    """

    # Fetch available templates
    templates_response = await get_pr_template()
    templates = json.loads(templates_response)

    # Tokenize the changes summary once
    summary_tokens = tokenize(changes_summary)

    # Step 1: Use Claude to dynamically classify change_type if not provided
    if not change_type or change_type.strip() == "":
        # Replace with actual call to Claude classify model as per your integration
        # Example placeholder:
        # change_type = await claude_classify(changes_summary)
        # For now fallback to 'feature'
        change_type = "feature"

    normalized_type = change_type.lower().strip()
    # Step 2: Score semantic similarity for each template via keywords
    scores = []
    for template in templates:
        keywords = TEMPLATE_KEYWORDS.get(template["filename"], set())
        score = compute_token_overlap_score(summary_tokens, keywords)
        scores.append((template, score))

    # Sort by score descending
    scores.sort(key=lambda x: x[1], reverse=True)

    # Step 3: Pick top scoring template, fallback to mapped template by type if no good score
    top_template, top_score = scores[0] if scores else (templates[0], 0.0)

    # If semantic score low (<0.2), fallback to type-based mapping
    if top_score < 0.2:
        fallback_file = TYPE_MAPPING.get(normalized_type, "feature.md")
        top_template = next((t for t in templates if t["filename"] == fallback_file), templates[0])
        top_score = 0.1  # Medium confidence

    # Build alternatives excluding selected
    alternatives = [t for t in templates if t["filename"] != top_template["filename"]][:3]

    confidence_level = "high" if top_score > 0.6 else "medium" if top_score > 0.3 else "low"

    suggestion = {
        "recommended_template": top_template,
        "alternatives": alternatives,
        "confidence_level": confidence_level,
        "confidence_score": top_score,
        "reasoning": (
            f"Based on semantic similarity between the changes summary and template keywords, "
            f"'{top_template['filename']}' was selected with confidence score {top_score:.2f}. "
            f"Original classification input was '{change_type}'."
        ),
        "template_content": top_template["content"],
        "usage_hint": "Claude can assist filling this template or consider alternatives if needed."
    }

    return {"result": json.dumps(suggestion)}


if __name__ == "__main__":
    mcp.run()
