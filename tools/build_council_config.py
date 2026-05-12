#!/usr/bin/env python3
"""Compile a council configuration markdown file into council_config.json.

Usage:
    uv run python tools/build_council_config.py INPUT [OUTPUT]

INPUT is a path to a council-config markdown file (format defined by the
H2_SECTIONS map and parse_markdown() below). OUTPUT is the destination JSON
path; if omitted, writes to <input-stem>.json next to the input file.

The script is stdlib-only and project-agnostic: it makes no assumptions about
where INPUT lives. The output JSON matches the schema enforced by the Pydantic
Settings model in `backend/settings.py`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

SETTINGS_SCALARS = {
    "search_provider",
    "search_keyword_extraction",
    "full_content_results",
    "search_result_count",
    "search_hybrid_mode",
    "show_free_only",
    "council_temperature",
    "chairman_temperature",
    "stage2_temperature",
    "chairman_filter",
    "ollama_base_url",
}

H2_SECTIONS = {
    "Settings",
    "Enabled Providers",
    "Direct Provider Toggles",
    "Council Models",
    "Council Member Filters",
    "Chairman Model",
    "Prompts",
}

PROMPT_SUBSECTIONS = {
    "Stage 1": "stage1_prompt",
    "Stage 2": "stage2_prompt",
    "Stage 3": "stage3_prompt",
}

REQUIRED_PLACEHOLDERS = {
    "stage1_prompt": {"{user_query}", "{search_context_block}"},
    "stage2_prompt": {"{user_query}", "{search_context_block}", "{responses_text}"},
    "stage3_prompt": {
        "{user_query}",
        "{search_context_block}",
        "{stage1_text}",
        "{stage2_text}",
    },
}

KNOWN_PLACEHOLDERS = {
    "{user_query}",
    "{search_context_block}",
    "{responses_text}",
    "{stage1_text}",
    "{stage2_text}",
}

SEARCH_PROVIDERS = {"duckduckgo", "tavily", "brave", "serper", "tinyfish"}

MODEL_RE = re.compile(r"^[a-z0-9_-]+:.+$")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")
H3_RE = re.compile(r"^###\s+(.+?)\s*$")
H1_RE = re.compile(r"^#\s+.+$")
FENCE_RE = re.compile(r"^````+\s*[a-zA-Z0-9_-]*\s*$")
KV_RE = re.compile(r"^([a-z_][a-z0-9_]*)\s*:\s*(.*)$")
LIST_RE = re.compile(r"^-\s+(.+?)\s*$")
PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")


def coerce_value(raw: str) -> bool | int | float | str:
    s = raw.strip()
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    try:
        if re.fullmatch(r"-?\d+", s):
            return int(s)
    except ValueError:
        pass
    try:
        if re.fullmatch(r"-?\d+\.\d+", s):
            return float(s)
    except ValueError:
        pass
    return s


def parse_markdown(text: str) -> dict:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    config: dict = {
        "enabled_providers": {},
        "direct_provider_toggles": {},
        "council_models": [],
        "council_member_filters": {},
        "prompts": {},
    }

    section: str | None = None
    subsection: str | None = None
    in_fence = False
    fence_buf: list[str] = []
    chairman_model_lines: list[str] = []

    errors: list[str] = []

    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()

        if in_fence:
            if FENCE_RE.match(line):
                if section == "Prompts" and subsection in PROMPT_SUBSECTIONS:
                    key = PROMPT_SUBSECTIONS[subsection]
                    config["prompts"][key] = "\n".join(fence_buf)
                fence_buf = []
                in_fence = False
            else:
                fence_buf.append(raw_line)
            continue

        if not line.strip():
            continue

        if H1_RE.match(line) and not line.startswith("##"):
            continue

        h2 = H2_RE.match(line)
        if h2:
            section = h2.group(1).strip()
            subsection = None
            if section not in H2_SECTIONS:
                errors.append(f"line {lineno}: unknown section '## {section}'")
            continue

        h3 = H3_RE.match(line)
        if h3:
            subsection = h3.group(1).strip()
            if section == "Prompts" and subsection not in PROMPT_SUBSECTIONS:
                errors.append(
                    f"line {lineno}: unknown prompt subsection '### {subsection}'"
                )
            continue

        if FENCE_RE.match(line):
            in_fence = True
            fence_buf = []
            continue

        if section is None:
            continue

        if section == "Settings":
            m = KV_RE.match(line)
            if not m:
                errors.append(f"line {lineno}: expected 'key: value' in Settings, got {line!r}")
                continue
            key, raw_val = m.group(1), m.group(2)
            if key not in SETTINGS_SCALARS:
                errors.append(f"line {lineno}: unknown Settings key '{key}'")
                continue
            config[key] = coerce_value(raw_val)

        elif section in ("Enabled Providers", "Direct Provider Toggles"):
            target = (
                "enabled_providers"
                if section == "Enabled Providers"
                else "direct_provider_toggles"
            )
            m = KV_RE.match(line)
            if not m:
                errors.append(f"line {lineno}: expected 'key: value' in {section}, got {line!r}")
                continue
            key, raw_val = m.group(1), m.group(2)
            val = coerce_value(raw_val)
            if not isinstance(val, bool):
                errors.append(
                    f"line {lineno}: {section} value for '{key}' must be true/false, got {raw_val!r}"
                )
                continue
            config[target][key] = val

        elif section == "Council Models":
            m = LIST_RE.match(line)
            if not m:
                errors.append(f"line {lineno}: expected '- model' list item, got {line!r}")
                continue
            config["council_models"].append(m.group(1).strip())

        elif section == "Council Member Filters":
            if line.strip() == "(empty)":
                continue
            m = KV_RE.match(line) or re.match(r"^(\d+)\s*:\s*(.*)$", line)
            if not m:
                errors.append(
                    f"line {lineno}: expected 'index: filter' or '(empty)' in {section}, got {line!r}"
                )
                continue
            raw_key, raw_val = m.group(1), m.group(2)
            try:
                idx = int(raw_key)
            except ValueError:
                errors.append(
                    f"line {lineno}: Council Member Filters keys must be integers, got {raw_key!r}"
                )
                continue
            config["council_member_filters"][idx] = raw_val.strip()

        elif section == "Chairman Model":
            chairman_model_lines.append(line.strip())

        elif section == "Prompts":
            errors.append(
                f"line {lineno}: text inside Prompts must be in a fenced block, got {line!r}"
            )

    if in_fence:
        errors.append("unterminated fenced code block at end of file")

    if chairman_model_lines:
        config["chairman_model"] = chairman_model_lines[0]

    if errors:
        raise ParseError(errors)

    return config


class ParseError(Exception):
    def __init__(self, errors: list[str]):
        super().__init__("\n".join(errors))
        self.errors = errors


def validate(config: dict) -> list[str]:
    errors: list[str] = []

    models = config.get("council_models", [])
    if not isinstance(models, list) or not all(isinstance(m, str) for m in models):
        errors.append("council_models must be a list of strings")
    else:
        if not (2 <= len(models) <= 8):
            errors.append(f"council_models length must be between 2 and 8 (got {len(models)})")
        if len(models) != len(set(models)):
            dupes = sorted({m for m in models if models.count(m) > 1})
            errors.append(f"duplicate council_models entries: {dupes}")
        for m in models:
            if not MODEL_RE.match(m):
                errors.append(f"council_models entry '{m}' must match 'provider:model-id'")

    chairman = config.get("chairman_model")
    if not isinstance(chairman, str) or not chairman.strip():
        errors.append("chairman_model is required and must be a non-empty string")
    elif not MODEL_RE.match(chairman):
        errors.append(f"chairman_model '{chairman}' must match 'provider:model-id'")

    prompts = config.get("prompts", {})
    for stage_key, required in REQUIRED_PLACEHOLDERS.items():
        body = prompts.get(stage_key)
        if not isinstance(body, str) or not body.strip():
            errors.append(f"prompts.{stage_key} is required and must be non-empty")
            continue
        missing = required - set(PLACEHOLDER_RE.findall(body))
        if missing:
            errors.append(
                f"prompts.{stage_key} missing required placeholders: {sorted(missing)}"
            )
        found = set(PLACEHOLDER_RE.findall(body))
        unknown = found - KNOWN_PLACEHOLDERS
        if unknown:
            errors.append(
                f"prompts.{stage_key} contains unknown placeholders: {sorted(unknown)}"
            )

    for key in ("council_temperature", "chairman_temperature", "stage2_temperature"):
        if key in config:
            val = config[key]
            if not isinstance(val, (int, float)) or not (0.0 <= float(val) <= 2.0):
                errors.append(f"{key} must be a number in [0.0, 2.0] (got {val!r})")

    sp = config.get("search_provider")
    if sp is not None and sp not in SEARCH_PROVIDERS:
        errors.append(
            f"search_provider '{sp}' must be one of {sorted(SEARCH_PROVIDERS)}"
        )

    for dkey in ("enabled_providers", "direct_provider_toggles"):
        d = config.get(dkey, {})
        if not isinstance(d, dict) or not all(
            isinstance(k, str) and isinstance(v, bool) for k, v in d.items()
        ):
            errors.append(f"{dkey} must be a dict of str → bool")

    cmf = config.get("council_member_filters", {})
    if not isinstance(cmf, dict) or not all(
        isinstance(k, int) and isinstance(v, str) for k, v in cmf.items()
    ):
        errors.append("council_member_filters must be a dict of int → str")

    fcr = config.get("full_content_results")
    src = config.get("search_result_count")
    if isinstance(fcr, int) and isinstance(src, int) and fcr > src:
        errors.append(
            f"full_content_results ({fcr}) must be <= search_result_count ({src})"
        )

    try:
        json.loads(json.dumps(config))
    except (TypeError, ValueError) as exc:
        errors.append(f"config does not round-trip through JSON: {exc}")

    return errors


def write_atomic(path: Path, payload: dict) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Compile council config markdown into council_config.json"
    )
    parser.add_argument("input", help="Path to the council config markdown source")
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Output JSON path (default: <input-stem>.json next to input)",
    )
    args = parser.parse_args(argv)

    in_path = Path(args.input)
    if not in_path.is_file():
        print(f"error: input file not found: {in_path}", file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else in_path.with_suffix(".json")

    try:
        text = in_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot read {in_path}: {exc}", file=sys.stderr)
        return 1

    try:
        config = parse_markdown(text)
    except ParseError as exc:
        print("parse errors:", file=sys.stderr)
        for line in exc.errors:
            print(f"  {line}", file=sys.stderr)
        return 1

    errors = validate(config)
    if errors:
        print("validation errors:", file=sys.stderr)
        for line in errors:
            print(f"  {line}", file=sys.stderr)
        return 1

    try:
        write_atomic(out_path, config)
    except OSError as exc:
        print(f"error: cannot write {out_path}: {exc}", file=sys.stderr)
        return 1

    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
