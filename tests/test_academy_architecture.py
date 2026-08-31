import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_academy_modules_do_not_import_firecrawl_transport():
    violations = []
    for path in (ROOT / "src/football_analytics").glob("academy_*.py"):
        tree = ast.parse(path.read_text())
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        if any(name.endswith("evidence_search") for name in imported):
            violations.append(path.name)

    assert violations == []
