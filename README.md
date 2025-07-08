# Github with PR Template Tools

The following illustrates basic Github MCP server that provides tools for analyzing git changes and suggesting
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

1. **analyze_file_changes** - Tool that analyzes Git changes between a base branch and HEAD to extract file change
   metadata, commit history, and optionally truncated diffs, for the purpose of PR template suggestions or automation.
    - Key Functionalities:
        - Detects changed files using git diff --name-status
        - Gathers diff statistics with git diff --stat
        - Fetches commit history since base_branch
        - Optionally captures full or truncated diffs (default max: 500 lines)
        - Auto-resolves working directory via MCP context or falls back to os.getcwd()
        - Returns a structured JSON with all change metadata
        - Debug metadata included (e.g., working directories, roots)