"""Render a PowerShell API snapshot into a documentation-only Starlight site.

No PowerShell or npm invocation occurs here. The extractor's JSON is the boundary.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path


VALID_COMMAND = re.compile(r"^[A-Za-z][A-Za-z0-9-]*$")
PLACEHOLDERS = ("{{fill", "todo", "tbd", "add a description", "insert description")


def frontmatter(title: str, description: str) -> str:
    return "---\ntitle: " + json.dumps(title, ensure_ascii=False) + "\ndescription: " + json.dumps(
        description, ensure_ascii=False) + "\n---\n\n"


def present(value: object) -> bool:
    text = str(value or "").strip()
    return bool(text) and not any(text.lower().startswith(word) for word in PLACEHOLDERS)


def authored_help(source: Path, command_name: str) -> str | None:
    if not source.exists():
        return None
    matches = [p for p in source.glob("*.md") if p.stem.casefold() == command_name.casefold()]
    if len(matches) > 1:
        raise ValueError(f"Duplicate authored help for {command_name}")
    if not matches:
        return None
    file = matches[0]
    if file.is_symlink():
        raise ValueError(f"Refusing symlinked documentation: {file}")
    return file.read_text(encoding="utf-8")


def has_authored_help(markdown: str) -> bool:
    sections = {}
    current = None
    for line in markdown.splitlines():
        match = re.match(r"^##\s+(SYNOPSIS|DESCRIPTION|EXAMPLES)\s*$", line, re.I)
        if match:
            current = match.group(1).lower()
            sections.setdefault(current, [])
        elif current is not None and not line.startswith("## "):
            sections[current].append(line)
        elif line.startswith("## "):
            current = None
    return all(present(" ".join(sections.get(name, [])).strip()) for name in
               ("synopsis", "description", "examples"))


def authored_parameters_complete(markdown: str, command: dict) -> bool:
    """Ensure authored help actually describes every exported public parameter."""
    for parameter in command.get("parameters", []):
        name = str(parameter.get("name", ""))
        match = re.search(r"(?im)^###\s+-?" + re.escape(name) + r"\s*$", markdown)
        if not match:
            return False
        body = re.split(r"(?m)^#{2,3}\s+", markdown[match.end():], maxsplit=1)[0]
        first = next((line.strip() for line in body.splitlines() if line.strip()), "")
        if not present(first) or first.lower().startswith(("type:", "default:", "required:", "parameter properties")):
            return False
    return True


def compose_reference(command: dict, strict: bool, override: str | None) -> str:
    name = command["name"]
    missing = []
    for key in ("synopsis", "description"):
        if not present(command.get(key)):
            missing.append(key)
    if not any(present(example.get("code")) for example in command.get("examples", [])):
        missing.append("examples")
    for param in command.get("parameters", []):
        if not present(param.get("description")):
            missing.append(f"parameter:{param.get('name', '')}")

    if strict and missing and not (
        override and has_authored_help(override) and authored_parameters_complete(override, command)
    ):
        raise ValueError(f"{name}: incomplete authored help: {', '.join(missing)}")
    synopsis = command.get("synopsis") or name
    content = [frontmatter(name, synopsis)]
    if override:
        # PlatyPS Markdown has its own metadata frontmatter. Starlight owns the new one.
        override = re.sub(r"\A---\r?\n.*?\r?\n---\r?\n", "", override, count=1, flags=re.S)
        content.append(override.strip() + "\n")
        return "".join(content)

    if missing:
        content.append("> **Documentation incomplete:** the module has missing descriptions or examples.\n\n")
    content.append(f"{html.escape(str(command.get('description') or 'No description provided.'))}\n\n")
    if command.get("syntax"):
        content.append("## Syntax\n\n```powershell\n" +
                       str(command["syntax"]).strip() + "\n```\n\n")
    if command.get("parameters"):
        content.append("## Parameters\n\n")
        for parameter in command["parameters"]:
            pname = str(parameter.get("name") or "")
            content.append(f"### -{html.escape(pname)}\n\n")
            content.append(html.escape(str(parameter.get("description") or
                                           "No parameter description provided.")) + "\n\n")
            content.append(f"- **Type:** `{str(parameter.get('type') or 'Object')}`\n")
            content.append(f"- **Required:** {'Yes' if parameter.get('required') else 'No'}\n\n")
    if command.get("examples"):
        content.append("## Examples\n\n")
        for i, example in enumerate(command["examples"], 1):
            content.append(f"### {html.escape(str(example.get('title') or f'Example {i}'))}\n\n")
            content.append("```powershell\n" + str(example.get("code", "")).strip() + "\n```\n\n")
            if example.get("description"):
                content.append(html.escape(str(example["description"])) + "\n\n")
    return "".join(content)


def build_site(reference: Path, site: Path, authored: Path | None = None,
               strict: bool = True) -> list[str]:
    data = json.loads(Path(reference).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("commands"), list):
        raise ValueError("Unsupported API reference schema")
    module = data.get("module", {})
    title = str(module.get("name", "PowerShell Module"))
    if not VALID_COMMAND.fullmatch(title):
        raise ValueError(f"Unsafe module name: {title!r}")
    docs = Path(site) / "src/content/docs"
    reference_path = docs / "reference"
    reference_path.mkdir(parents=True, exist_ok=True)

    if authored and (Path(authored) / "guides").is_dir():
        for guide in sorted((Path(authored) / "guides").rglob("*.md")):
            if guide.is_symlink():
                raise ValueError(f"Symlinked guide not supported: {guide}")
            dest = docs / "guides" / guide.relative_to(Path(authored) / "guides")
            dest.parent.mkdir(parents=True, exist_ok=True)
            text = guide.read_text(encoding="utf-8")
            if not text.startswith("---\n"):
                text = frontmatter(guide.stem.replace("-", " ").title(), "Module guide") + text
            dest.write_text(text, encoding="utf-8")

    names = []
    seen = set()
    for command in data["commands"]:
        name = str(command.get("name", ""))
        if not VALID_COMMAND.fullmatch(name) or name.casefold() in seen:
            raise ValueError(f"Unsafe or duplicate command: {name!r}")
        seen.add(name.casefold())
        override = authored_help(Path(authored), name) if authored else None
        rendered = compose_reference(command, strict, override)
        (reference_path / f"{name.lower()}.md").write_text(rendered, encoding="utf-8")
        names.append(name)

    if not names:
        raise ValueError(f"No exported commands found in module {title}")
    overview = [
        frontmatter(title, f"Documentation for the {title} PowerShell module"),
        f"# {html.escape(title)}\n\n",
        f"{html.escape(str(module.get('description') or 'PowerShell module reference.'))}\n\n",
        "## Command reference\n\n",
    ]
    overview += [f"- [{name}](./reference/{name.lower()}/)\n" for name in names]
    (docs / "index.md").write_text("".join(overview), encoding="utf-8")
    return names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--site", required=True, type=Path)
    parser.add_argument("--authored", default="", type=str)
    parser.add_argument("--strict", choices=["true", "false"], default="true")
    args = parser.parse_args()
    names = build_site(args.reference, args.site, Path(args.authored) if args.authored else None,
                       strict=args.strict == "true")
    print(f"Generated {len(names)} command reference pages: {', '.join(names)}")


if __name__ == "__main__":
    main()
