# Github with PR Template Tools

The following illustrates basic GitHub MCP server that provides tools for analyzing git changes and suggesting
appropriate PR
templates.

## Setup

### 1. Install uv

Follow the official installation instructions at: https://docs.astral.sh/uv/getting-started/installation/

### 2. Install dependencies

```bash
# Install all dependencies
uv sync

# Or install with dev dependencies for testing
uv sync --all-extras
```

### 3. Configure the MCP Server

Add the server to Claude Code:

```bash
# Add the MCP server
claude mcp add pr-agent -- uv --directory /absolute/path/to/module1/solution run server.py

# Verify it's configured
claude mcp list
```

## Tools Available

1. `````**analyze_file_changes**`````: Analyzes Git changes between a base branch and HEAD to extract file-level
   modifications,
   commit history, and optionally truncated diffs — enabling automated PR generation, impact assessment, or review
   workflows.

- Key Functionalities:
    - Parses changed files via ```git diff --name-status``` into structured JSON:
      ```[{ "status": "M", "file": "main.py" }, ...]```
    - Fetches change statistics via ```git diff --stat```
    - Captures commit history using ```git log --oneline```
    - Optionally includes full or truncated diff (default: 500 lines)
    - Smart fallback logic:
    - Uses ```mcp.get_context().session.list_roots()``` to infer working directory
    - Defaults to ```os.getcwd()``` if context is unavailable
    - Embeds a rich ```_debug``` block with root info, working directory trace, and server context


2. ```**get_pr_template**```: Fetches the available PR templates from the shared template directory, including
   content and
   metadata — ready to be displayed, edited, or autofilled by Claude or similar agents.

- Key Functionalities:
    - Loads all templates defined in ```DEFAULT_TEMPLATES``` (e.g., ```bug.md```, ```feature.md```, ```docs.md```, etc.)
    - Reads the content of each template file from disk
    - Fails gracefully if a file is missing or unreadable (```Error loading template...```)
    - Returns metadata alongside the file body: ```filename```, ```type```, ```content```


3. ```**suggest_templates**```: Provides Claude-friendly PR template recommendations based on a natural language change
   summary and change type (e.g., "bug", "feature"). Suggests the best-fit template and alternatives with reasoning and
   confidence level.

- Key Functionalities:
    - Normalizes change_type using a semantic map (TYPE_MAPPING)
    - Selects a recommended template (or defaults to feature.md)
    - Includes 2–3 alternatives to support Claude in ambiguous scenarios
    - Adds reasoning and confidence level ("high"/"medium")
    - Embeds the full template content to support AI-based autofill or mutation

- Inputs:
- ```changes_summary```: natural language summary of the diff
- ```change_type```: one of bug, feature, docs, refactor, performance, etc.

## Future Improvements:

- Expose this as a web tool or MCP extension
- Embed automatic PR generation directly into GitHub Actions
- Integrate template generation with LLM-assisted refactoring

## Author

#### Udayan Sawant | Generative AI Engineer

#### Building intelligent tools for the future of developer productivity