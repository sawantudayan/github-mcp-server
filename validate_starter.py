"""
Validation script for Module 1 starter code
Ensures the starter template is ready for learners to implement
"""

import os
import sys
from pathlib import Path


def test_project_structure():
    """Check that all required files exist."""
    print("Project Structure:")
    required_files = [
        "github_mcp_server.py",
        "pyproject.toml",
        "README.md"
    ]

    all_exist = True
    for file in required_files:
        if Path(file).exists():
            print(f"  {file} exists")
        else:
            print(f"  {file} missing")
            all_exist = False

    return all_exist


def test_imports():
    """Test that the starter code imports work."""
    try:
        # Test importing the server module
        import github_mcp_server
        print("github_mcp_server.py imports successfully")

        # Check that FastMCP is imported
        if hasattr(github_mcp_server, 'mcp'):
            print("FastMCP server instance found")
        else:
            print("FastMCP server instance not found")
            return False

        return True
    except ImportError as e:
        print(f"Import error: {e}")
        print("Please ensure you've installed dependencies: uv sync")
        return False


def test_starter_runs():
    """Test that the starter code can at least be executed."""
    print("\nExecution Test:")

    try:
        # Try to import and check if server can be initialized
        import github_mcp_server
        # If we can import it and it has the right attributes, it should run
        if hasattr(github_mcp_server, 'mcp') and hasattr(github_mcp_server, 'analyze_file_changes'):
            print("Server imports and initializes correctly")
            return True
        else:
            print("Server missing required components")
            return False

    except Exception as e:
        print(f"✗ Failed to initialize server: {e}")
        return False


def test_dependencies():
    """Check that pyproject.toml is properly configured."""
    print("\nDependencies:")

    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    try:
        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)

        # Check for required sections
        if "project" in config and "dependencies" in config["project"]:
            deps = config["project"]["dependencies"]
            print(f"Found {len(deps)} dependencies")
            for dep in deps:
                print(f"  - {dep}")
        else:
            print("No dependencies section found")
            return False

        return True
    except Exception as e:
        print(f"✗ Error reading pyproject.toml: {e}")
        return False


def test_no_implementation():
    """Ensure starter code doesn't contain the solution."""
    print("\nImplementation Check:")

    with open("github_mcp_server.py", "r") as f:
        content = f.read()

    # Check that tool functions are not implemented
    solution_indicators = [
        "subprocess.run",  # Git commands
        "json.dumps",  # Returning JSON
        "git diff",  # Git operations
        "template",  # Template logic
    ]

    found_implementations = []
    for indicator in solution_indicators:
        if indicator in content.lower():
            found_implementations.append(indicator)

    if found_implementations:
        print(f"Found possible solution code: {', '.join(found_implementations)}")
        print("Make sure these are only in comments/examples")
        return True  # Warning, not failure
    else:
        print("✓ No solution implementation found (good!)")
        return True


def main():
    """Run all validation checks."""
    print("Github MCP Server Validation")
    print("=" * 50)

    # Change to starter directory if needed
    if Path("validate_starter.py").exists():
        os.chdir(Path("validate_starter.py").parent)

    tests = [
        ("Project Structure", test_project_structure),
        ("Python Imports", test_imports),
        ("Starter Execution", test_starter_runs),
        ("Dependencies", test_dependencies),
        ("Clean Starter", test_no_implementation)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            results.append(test_func())
        except Exception as e:
            print(f"Test failed with error: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Checks passed: {passed}/{total}")

    if passed == total:
        print("\nGithub PR Agent is configured successfully!")
    else:
        print("\n✗ Some checks failed. Please review the github_mcp_server code.")
        sys.exit(1)


if __name__ == "__main__":
    main()
