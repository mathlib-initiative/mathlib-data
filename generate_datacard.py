#!/usr/bin/env python3
"""Generate a HuggingFace datacard README from a template and lean_scout schema."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader


def get_mathlib_commit() -> str:
    """Extract mathlib commit hash from lake-manifest.json."""
    manifest_path = Path("lake-manifest.json")
    manifest = json.loads(manifest_path.read_text())
    for pkg in manifest["packages"]:
        if pkg["name"] == "mathlib":
            return pkg["rev"]
    raise ValueError("mathlib not found in lake-manifest.json")


def get_schema(schema_type: str) -> dict:
    """Run lake exe lean_scout_schema to get the JSON schema."""
    result = subprocess.run(
        ["lake", "exe", "lean_scout_schema", schema_type],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error running lean_scout_schema: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # stdout contains the JSON (build messages go to stderr)
    return json.loads(result.stdout)


def format_json(value: dict, indent: int = 2) -> str:
    """Jinja2 filter to format a dict as pretty JSON."""
    return json.dumps(value, indent=indent)


def format_yaml(value: dict) -> str:
    """Jinja2 filter to format a dict as YAML."""
    return yaml.dump(value, default_flow_style=False, sort_keys=False).rstrip()


def generate_datacard(template_path: Path) -> str:
    """Generate the datacard using Jinja2 templating."""
    env = Environment(
        loader=FileSystemLoader(template_path.parent),
        keep_trailing_newline=True,
    )
    env.filters["json"] = format_json
    env.filters["yaml"] = format_yaml

    template = env.get_template(template_path.name)
    schema = get_schema("types")

    return template.render(schema=schema, mathlib_commit=get_mathlib_commit())


def main():
    parser = argparse.ArgumentParser(
        description="Generate a HuggingFace datacard from a template"
    )
    parser.add_argument(
        "template",
        type=Path,
        help="Path to the template file (e.g., README.types.template.md)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file path (default: stdout)",
    )

    args = parser.parse_args()

    if not args.template.exists():
        print(f"Error: Template file not found: {args.template}", file=sys.stderr)
        sys.exit(1)

    datacard = generate_datacard(args.template)

    if args.output:
        args.output.write_text(datacard)
        print(f"Generated datacard: {args.output}")
    else:
        print(datacard)


if __name__ == "__main__":
    main()
