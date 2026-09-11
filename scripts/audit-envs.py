#!/usr/bin/env python3
"""
Audits, synchronizes, and cleans .env, .env.*, and .env.example files
without printing environment variable values.

Rules:
- Real environment files:
    .env, .env.prod, .env.local, .env.staging, and any other .env.* file.
- Reference file:
    .env.example.
- .env / .env.* -> .env.example:
    adds only KEY= and never copies the real value.
- .env.example -> each existing .env / .env.*:
    copies the complete KEY=value/default block from the example file.
- Only .env / .env.* files exist:
    creates .env.example using the union of keys from all environment files.
- Only .env.example exists:
    creates .env from the example file, provided that no potential real secret
    is detected.
- Variables with no detected runtime/configuration references:
    are automatically removed from all .env / .env.* files and .env.example.
- Variables with weak usage evidence:
    are preserved automatically.
- Keys listed in ignore_unused_keys:
    are preserved automatically.

By default, when executed without additional options, the script:
1. synchronizes all .env / .env.* files with the .env.example in the same
   directory;
2. audits environment variable usage;
3. automatically removes variables with no detected usage from all related
   environment files;
4. reports which variables were removed.

Use --dry-run to simulate synchronization and cleanup without modifying files.
Use --audit-only to analyze files without making changes.
Use --strict to fail on key mismatches, duplicate keys, or potential secrets.
Use --strict --strict-unused to also fail when a variable has no detected
runtime/configuration reference.

The script never prints environment variable values.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------

IGNORED_DIR_NAMES = {
    ".git",
    ".idea",
    ".vscode",
    ".env-audit-backups",
    "node_modules",
    "storage",
    "vendor",
    "__pycache__",
}

IGNORED_PATHS = {
    "bootstrap/cache",
    "public/build",
}

DOCUMENTATION_NAMES = {
    "README",
    "README.md",
    "README.txt",
    "CHANGELOG",
    "CHANGELOG.md",
    "LICENSE",
    "LICENSE.md",
}

DOCUMENTATION_SUFFIXES = {
    ".md",
    ".rst",
    ".adoc",
}

BINARY_OR_ASSET_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".tgz",
    ".7z",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".mp3",
    ".mp4",
    ".wav",
    ".ogg",
    ".webm",
    ".jar",
    ".class",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".sqlite",
    ".db",
}

DEFAULT_PUBLIC_NON_SECRET_KEYS: set[str] = set()

SECRET_NAME_RE = re.compile(
    r"(?:^|_)(?:SECRET|PASSWORD|PASS|TOKEN|PRIVATE|CREDENTIALS?|"
    r"CLIENT_SECRET|APP_KEY|API_KEY)(?:_|$)",
    re.IGNORECASE,
)

SAFE_PLACEHOLDER_RE = re.compile(
    r"^(?:"
    r"|null|false|true|0|1"
    r"|base64:"
    r"|change(?:me)?"
    r"|trocar"
    r"|placeholder"
    r"|example"
    r"|dummy"
    r"|fake"
    r"|your[_-]?.*"
    r"|x{3,}"
    r"|<.*>"
    r")$",
    re.IGNORECASE,
)

ENV_LINE_RE = re.compile(
    r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*="
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@dataclass
class EnvEntry:
    key: str
    value: str
    block: str


@dataclass
class EnvFile:
    path: Path
    keys: list[str]
    entries: dict[str, EnvEntry]
    duplicates: list[str]

    @property
    def values(self) -> dict[str, str]:
        return {
            key: entry.value
            for key, entry in self.entries.items()
        }


@dataclass
class AuditConfig:
    public_non_secret_keys: set[str] = field(
        default_factory=lambda: set(DEFAULT_PUBLIC_NON_SECRET_KEYS)
    )
    ignore_unused_keys: set[str] = field(default_factory=set)
    ignore_projects: set[str] = field(default_factory=set)
    ignore_files: set[str] = field(default_factory=set)


@dataclass
class UsageEvidence:
    strong: set[Path] = field(default_factory=set)
    weak: set[Path] = field(default_factory=set)


@dataclass
class SyncAction:
    target: Path
    kind: str
    keys: list[str]


# ---------------------------------------------------------------------------
# Optional external configuration
# ---------------------------------------------------------------------------

def load_audit_config(root: Path) -> AuditConfig:
    """
    Optional file: <root>/.env-audit.json

    Example:
    {
        "public_non_secret_keys": ["PUBLIC_CLIENT_KEY"],
        "ignore_unused_keys": ["SUPPORTED_LEGACY_VARIABLE"],
        "ignore_projects": ["legacy-project"],
        "ignore_files": ["generated/config.js"]
    }
    """
    config = AuditConfig()
    path = root / ".env-audit.json"

    if not path.exists():
        return config

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Failed to read {path}: {exc}") from exc

    config.public_non_secret_keys.update(
        data.get("public_non_secret_keys", [])
    )
    config.ignore_unused_keys.update(
        data.get("ignore_unused_keys", [])
    )
    config.ignore_projects.update(
        data.get("ignore_projects", [])
    )
    config.ignore_files.update(
        data.get("ignore_files", [])
    )

    return config


# ---------------------------------------------------------------------------
# Filesystem
# ---------------------------------------------------------------------------

def is_ignored(
    path: Path,
    config: AuditConfig | None = None,
) -> bool:
    if any(part in IGNORED_DIR_NAMES for part in path.parts):
        return True

    normalized = "/" + path.as_posix().strip("/") + "/"

    if any(
        f"/{ignored.strip('/')}/" in normalized
        for ignored in IGNORED_PATHS
    ):
        return True

    if config:
        for ignored in config.ignore_files:
            needle = ignored.strip("/")

            if (
                normalized.endswith(f"/{needle}/")
                or f"/{needle}/" in normalized
            ):
                return True

    return False


def is_documentation(path: Path) -> bool:
    if path.name in DOCUMENTATION_NAMES:
        return True

    if path.suffix.lower() in DOCUMENTATION_SUFFIXES:
        return True

    lowered_parts = {
        part.lower()
        for part in path.parts
    }

    return bool(
        lowered_parts
        & {
            "docs",
            "doc",
            "documentation",
        }
    )


def is_env_runtime_file(path: Path) -> bool:
    """
    Returns True for real environment files.

    Includes:
    - .env
    - .env.prod
    - .env.local
    - .env.staging
    - any other .env.* file

    Excludes:
    - .env.example
    - .env*.bak.* backup files
    """
    name = path.name

    if name == ".env":
        return True

    if not name.startswith(".env."):
        return False

    if name == ".env.example":
        return False

    if ".bak." in name:
        return False

    return True


def is_searchable_runtime_file(
    path: Path,
    config: AuditConfig,
) -> bool:
    # .env files are configuration sources, not evidence of usage.
    if (
        is_env_runtime_file(path)
        or path.name == ".env.example"
        or path.name == ".env-audit.json"
    ):
        return False

    if ".bak." in path.name and path.name.startswith(".env"):
        return False

    if is_ignored(path, config) or is_documentation(path):
        return False

    if path.suffix.lower() in BINARY_OR_ASSET_SUFFIXES:
        return False

    return path.is_file()


# ---------------------------------------------------------------------------
# .env parser with multiline block support
# ---------------------------------------------------------------------------

def _strip_outer_quotes(value: str) -> str:
    value = value.strip()

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        return value[1:-1]

    return value


def _quote_is_open(
    raw_value: str,
) -> str | None:
    """
    Returns the type of open quote (' or ") when an assignment starts a
    literal multiline value.

    Simple escape sequences are taken into account.
    """
    stripped = raw_value.lstrip()

    if (
        not stripped
        or stripped[0] not in {"'", '"'}
    ):
        return None

    quote = stripped[0]
    escaped = False

    for ch in stripped[1:]:
        if escaped:
            escaped = False
            continue

        if ch == "\\":
            escaped = True
            continue

        if ch == quote:
            return None

    return quote


def parse_env(path: Path) -> EnvFile:
    lines = path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    keys: list[str] = []
    entries: dict[str, EnvEntry] = {}

    i = 0

    while i < len(lines):
        line = lines[i]
        match = ENV_LINE_RE.match(line)

        if not match:
            i += 1
            continue

        key = match.group(1)
        block_lines = [line]
        raw_value = line.split("=", 1)[1].strip()
        open_quote = _quote_is_open(raw_value)

        if open_quote:
            j = i + 1

            while j < len(lines):
                block_lines.append(lines[j])

                current = lines[j]
                escaped = False
                closed = False

                for ch in current:
                    if escaped:
                        escaped = False
                        continue

                    if ch == "\\":
                        escaped = True
                        continue

                    if ch == open_quote:
                        closed = True
                        break

                if closed:
                    break

                j += 1

            i = j

        block = "\n".join(block_lines)
        value_part = block.split("=", 1)[1].strip()
        value = _strip_outer_quotes(value_part)

        keys.append(key)
        entries[key] = EnvEntry(
            key=key,
            value=value,
            block=block,
        )

        i += 1

    duplicates = sorted(
        key
        for key, count in Counter(keys).items()
        if count > 1
    )

    return EnvFile(
        path=path,
        keys=keys,
        entries=entries,
        duplicates=duplicates,
    )


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_projects(
    root: Path,
    config: AuditConfig,
) -> list[
    tuple[
        Path,
        list[Path],
        Path | None,
    ]
]:
    """
    Discovers all .env / .env.* files and the .env.example file in each directory.

    Each directory is treated as a single project/environment set:
        .env
        .env.prod
        .env.local
        ...
        .env.example
    """
    projects: list[
        tuple[
            Path,
            list[Path],
            Path | None,
        ]
    ] = []

    for current_root, dirnames, filenames in os.walk(root):
        current = Path(current_root)

        dirnames[:] = [
            name
            for name in dirnames
            if not is_ignored(current / name, config)
        ]

        rel = current.relative_to(root).as_posix()

        if rel in config.ignore_projects:
            dirnames[:] = []
            continue

        env_paths = sorted(
            [
                current / filename
                for filename in filenames
                if is_env_runtime_file(current / filename)
            ],
            key=lambda path: (
                path.name != ".env",
                path.name,
            ),
        )

        example_path = (
            current / ".env.example"
            if ".env.example" in filenames
            else None
        )

        if env_paths or example_path:
            projects.append(
                (
                    current,
                    env_paths,
                    example_path,
                )
            )

    return sorted(
        projects,
        key=lambda item: item[0].as_posix(),
    )


def iter_runtime_files(
    project_dir: Path,
    config: AuditConfig,
) -> list[Path]:
    result: list[Path] = []

    for current_root, dirnames, filenames in os.walk(project_dir):
        current = Path(current_root)

        dirnames[:] = [
            name
            for name in dirnames
            if not is_ignored(current / name, config)
        ]

        for filename in filenames:
            path = current / filename

            if is_searchable_runtime_file(path, config):
                result.append(path)

    return result


# ---------------------------------------------------------------------------
# Usage Detection
# ---------------------------------------------------------------------------

STRONG_USAGE_EXTRACTORS: list[re.Pattern[str]] = [
    # PHP / Laravel
    re.compile(
        r"""env\s*\(\s*['"]([A-Za-z_][A-Za-z0-9_]*)['"]"""
    ),

    # Docker Compose / Shell interpolation
    re.compile(
        r"""\$\{([A-Za-z_][A-Za-z0-9_]*)(?::[-+?][^}]*)?\}"""
    ),

    # Simple Shell $VAR
    re.compile(
        r"""(?<![A-Za-z0-9_])\$([A-Za-z_][A-Za-z0-9_]*)(?![A-Za-z0-9_])"""
    ),

    # Node
    re.compile(
        r"""process\.env\.([A-Za-z_][A-Za-z0-9_]*)"""
    ),
    re.compile(
        r"""process\.env\[\s*['"]([A-Za-z_][A-Za-z0-9_]*)['"]\s*\]"""
    ),

    # Vite
    re.compile(
        r"""import\.meta\.env\.([A-Za-z_][A-Za-z0-9_]*)"""
    ),

    # Python
    re.compile(
        r"""os\.getenv\s*\(\s*['"]([A-Za-z_][A-Za-z0-9_]*)['"]"""
    ),
    re.compile(
        r"""os\.environ(?:\.get)?\s*\(\s*['"]([A-Za-z_][A-Za-z0-9_]*)['"]"""
    ),
    re.compile(
        r"""os\.environ\[\s*['"]([A-Za-z_][A-Za-z0-9_]*)['"]\s*\]"""
    ),

    # Java / Kotlin
    re.compile(
        r"""System\.getenv\s*\(\s*['"]([A-Za-z_][A-Za-z0-9_]*)['"]"""
    ),

    # Custom helpers
    re.compile(
        r"""(?:getRequiredEnv|getEnv|getNumberEnv|getListEnv|"""
        r"""getRequiredEnvFrom|getNumberEnvFrom|getListEnvFrom)"""
        r"""\s*\([^)]*?['"]([A-Za-z_][A-Za-z0-9_]*)['"]"""
    ),
]

DOCKERFILE_ENV_RE = re.compile(
    r"""(?m)^\s*(?:ARG|ENV)\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s|=|$)"""
)

ENV_TOKEN_RE = re.compile(
    r"""(?<![A-Za-z0-9_])([A-Z][A-Z0-9_]*)(?![A-Za-z0-9_])"""
)


def analyze_usage(
    keys: Iterable[str],
    files: list[Path],
    *,
    progress: bool = False,
) -> dict[str, UsageEvidence]:
    """
    Analyzes usage in O(files), rather than O(variables × files).

    For each file:
    1. reads the content only once;
    2. extracts all strong references;
    3. extracts UPPER_CASE tokens as weak evidence;
    4. matches them against the known environment variables.
    """
    key_set = set(keys)

    evidence = {
        key: UsageEvidence()
        for key in key_set
    }

    total = len(files)

    for index, path in enumerate(files, start=1):
        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except (OSError, UnicodeError):
            continue

        strong_found: set[str] = set()

        for extractor in STRONG_USAGE_EXTRACTORS:
            strong_found.update(extractor.findall(text))

        strong_found.update(
            DOCKERFILE_ENV_RE.findall(text)
        )

        strong_found &= key_set

        for key in strong_found:
            evidence[key].strong.add(path)

        weak_found = (
            set(ENV_TOKEN_RE.findall(text))
            & key_set
        )

        for key in weak_found - strong_found:
            evidence[key].weak.add(path)

        if progress and total:
            if (
                index == 1
                or index == total
                or index % 250 == 0
            ):
                print(
                    f"  Analyzing usage: {index}/{total} files",
                    flush=True,
                )

    return evidence


# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------

def _looks_like_safe_placeholder(
    value: str,
) -> bool:
    normalized = value.strip()

    return (
        not normalized
        or bool(
            SAFE_PLACEHOLDER_RE.fullmatch(normalized)
        )
    )


def suspicious_example_keys(
    example: EnvFile,
    config: AuditConfig,
) -> list[str]:
    keys: list[str] = []

    for key, entry in example.entries.items():
        if key in config.public_non_secret_keys:
            continue

        if not SECRET_NAME_RE.search(key):
            continue

        if not _looks_like_safe_placeholder(entry.value):
            keys.append(key)

    return sorted(keys)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_key_list(
    title: str,
    keys: list[str],
) -> None:
    if not keys:
        return

    print(f"  {title}:")

    for key in keys:
        print(f"    - {key}")


def print_usage_summary(
    evidence: dict[str, UsageEvidence],
    root: Path,
    *,
    show_usage: bool,
) -> tuple[
    list[str],
    list[str],
]:
    weak_usage_only: list[str] = []
    unused: list[str] = []

    for key, item in sorted(evidence.items()):
        if item.strong:
            if show_usage:
                paths = ", ".join(
                    sorted(
                        str(path.relative_to(root))
                        for path in item.strong
                    )
                )

                print(
                    f"  STRONG_USAGE {key}: {paths}"
                )

            continue

        if item.weak:
            weak_usage_only.append(key)

            if show_usage:
                paths = ", ".join(
                    sorted(
                        str(path.relative_to(root))
                        for path in item.weak
                    )
                )

                print(
                    f"  WEAK_USAGE {key}: {paths}"
                )

        else:
            unused.append(key)

    return weak_usage_only, unused


# ---------------------------------------------------------------------------
# Write / backup
# ---------------------------------------------------------------------------

def ensure_trailing_newline(
    content: str,
) -> str:
    if not content:
        return ""

    return content.rstrip("\n") + "\n"


def backup_path_for(
    root: Path,
    path: Path,
) -> Path:
    rel = path.relative_to(root)

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    return (
        root
        / ".env-audit-backups"
        / rel.parent
        / f"{rel.name}.{timestamp}.bak"
    )


def create_backup(
    root: Path,
    path: Path,
) -> Path | None:
    if not path.exists():
        return None

    backup = backup_path_for(root, path)

    backup.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        backup.parent.chmod(0o700)
    except OSError:
        pass

    shutil.copy2(path, backup)

    try:
        backup.chmod(0o600)
    except OSError:
        pass

    return backup


def append_section(
    root: Path,
    path: Path,
    title: str,
    blocks: list[str],
    *,
    backup: bool,
    dry_run: bool,
) -> None:
    if not blocks or dry_run:
        return

    if backup:
        create_backup(root, path)

    existing = ""

    if path.exists():
        existing = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    existing = ensure_trailing_newline(existing)

    if existing:
        existing += "\n"

    existing += (
        "# ------------------------------------------------------------------\n"
        f"# {title}\n"
        "# Automatically added by scripts/audit-envs.py\n"
        "# ------------------------------------------------------------------\n"
    )

    existing += "\n".join(blocks)
    existing += "\n"

    path.write_text(
        existing,
        encoding="utf-8",
    )


def create_example_from_envs(
    envs: list[EnvFile],
    example_path: Path,
    *,
    dry_run: bool,
) -> None:
    """
    Creates .env.example using the union of keys from all .env / .env.* files.

    Real values are never copied.
    """
    if dry_run:
        return

    keys: list[str] = []
    seen: set[str] = set()

    for env in envs:
        for key in env.keys:
            if key not in seen:
                seen.add(key)
                keys.append(key)

    lines = [
        "# Automatically generated from the keys of .env / .env.* files.",
        "# Real values were NOT copied.",
        "",
    ]

    for key in keys:
        lines.append(f"{key}=")

    lines.append("")

    example_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def create_env_from_example(
    example: EnvFile,
    env_path: Path,
    *,
    dry_run: bool,
) -> None:
    if dry_run:
        return

    source = example.path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    env_path.write_text(
        source,
        encoding="utf-8",
    )


def remove_keys_from_env_file(
    root: Path,
    path: Path,
    keys: Iterable[str],
    *,
    backup: bool,
    dry_run: bool,
) -> list[str]:
    """
    Remove assignments KEY=... from an .env/.env.example file.

    - Supports multiline values between quotes.
    - Preserves comments and other lines.
    - Never prints values.
    - Returns the keys found in the file.
    """
    keys_to_remove = set(keys)

    if not keys_to_remove or not path.exists():
        return []

    lines = path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    output: list[str] = []
    removed: list[str] = []

    i = 0

    while i < len(lines):
        line = lines[i]
        match = ENV_LINE_RE.match(line)

        if not match:
            output.append(line)
            i += 1
            continue

        key = match.group(1)

        if key not in keys_to_remove:
            output.append(line)
            i += 1
            continue

        removed.append(key)

        raw_value = line.split("=", 1)[1].strip()
        open_quote = _quote_is_open(raw_value)

        i += 1

        if open_quote:
            while i < len(lines):
                current = lines[i]
                escaped = False
                closed = False

                for ch in current:
                    if escaped:
                        escaped = False
                        continue

                    if ch == "\\":
                        escaped = True
                        continue

                    if ch == open_quote:
                        closed = True
                        break

                i += 1

                if closed:
                    break

    removed = sorted(set(removed))

    if not removed or dry_run:
        return removed

    if backup:
        create_backup(root, path)

    content = "\n".join(output)

    if content:
        content = content.rstrip("\n") + "\n"

    path.write_text(
        content,
        encoding="utf-8",
    )

    return removed


# ---------------------------------------------------------------------------
# Synchronization
# ---------------------------------------------------------------------------

def sync_project(
    root: Path,
    directory: Path,
    env_paths: list[Path],
    example_path: Path | None,
    config: AuditConfig,
    *,
    backup: bool,
    dry_run: bool,
) -> tuple[
    list[Path],
    Path | None,
    list[SyncAction],
]:
    """
    Synchronizes an entire set of environment files.

    The .env.example is the common reference:
    - it receives the union of keys from all .env / .env.* files;
    - each .env / .env.* receives keys that are present in .env.example
      but missing from that environment file.
    """
    actions: list[SyncAction] = []

    existing_envs = [
        parse_env(path)
        for path in env_paths
        if path.exists()
    ]

    # One or more .env/.env.* files exist, but .env.example does not.
    if existing_envs and not example_path:
        example_path = directory / ".env.example"

        union_keys = sorted(
            {
                key
                for env in existing_envs
                for key in env.keys
            }
        )

        actions.append(
            SyncAction(
                example_path,
                "CREATE_EXAMPLE_FROM_ENVS",
                union_keys,
            )
        )

        source_names = ", ".join(
            env.path.name
            for env in existing_envs
        )

        print(
            f"  SYNC: would create .env.example from keys in: {source_names}"
            if dry_run
            else
            f"  SYNC: creating .env.example from keys in: {source_names}"
        )

        create_example_from_envs(
            existing_envs,
            example_path,
            dry_run=dry_run,
        )

        # In dry-run mode, the file does not physically exist; the planned actions
        # will be used by the virtual audit.
        if not dry_run:
            example_path = directory / ".env.example"

    # Only .env.example exists: preserve the existing behavior and create .env.
    elif example_path and not existing_envs:
        example = parse_env(example_path)

        suspicious = suspicious_example_keys(
            example,
            config,
        )

        if suspicious:
            print(
                "  ERROR: .env.example contains possible secret; "
                "automatic creation of .env was blocked."
            )

            print_key_list(
                "POSSIBLE_SECRET_IN_EXAMPLE",
                suspicious,
            )

            return env_paths, example_path, actions

        env_path = directory / ".env"
        keys = list(dict.fromkeys(example.keys))

        actions.append(
            SyncAction(
                env_path,
                "CREATE_ENV_FROM_EXAMPLE",
                keys,
            )
        )

        print(
            "  SYNC: would create .env from .env.example"
            if dry_run
            else
            "  SYNC: creating .env from .env.example"
        )

        create_env_from_example(
            example,
            env_path,
            dry_run=dry_run,
        )

        if env_path not in env_paths:
            env_paths = [env_path, *env_paths]

        if not dry_run:
            existing_envs = [parse_env(env_path)]

    if not example_path:
        return env_paths, example_path, actions

    # If the example file was planned during dry-run, there is no physical file to parse yet.
    example_exists = example_path.exists()

    if example_exists:
        example = parse_env(example_path)

        suspicious = suspicious_example_keys(
            example,
            config,
        )

        if suspicious:
            print(
                "  ERROR: synchronization blocked until "
                "possible secret in .env.example is corrected."
            )

            print_key_list(
                "POSSIBLE_SECRET_IN_EXAMPLE",
                suspicious,
            )

            return env_paths, example_path, actions
    else:
        example = None

    # Union of keys present across all real environment files.
    env_union_keys = {
        key
        for env in existing_envs
        for key in env.keys
    }

    example_keys = (
        set(example.keys)
        if example
        else set()
    )

    # If the example file was planned during dry-run, its virtual view already
    # contains the union of keys from the environment files.
    if dry_run and any(
        action.kind == "CREATE_EXAMPLE_FROM_ENVS"
        for action in actions
    ):
        example_keys |= env_union_keys

    missing_from_example = sorted(
        env_union_keys - example_keys
    )

    if missing_from_example and example_path:
        actions.append(
            SyncAction(
                example_path,
                "ADD_KEYS_TO_EXAMPLE",
                missing_from_example,
            )
        )

        verb = (
            "would add"
            if dry_run
            else "adding"
        )

        print(
            f"  SYNC: {verb} to .env.example: "
            + ", ".join(missing_from_example)
        )

        append_section(
            root,
            example_path,
            "Variables synchronized from .env / .env.* files",
            [
                f"{key}="
                for key in missing_from_example
            ],
            backup=backup,
            dry_run=dry_run,
        )

        example_keys.update(missing_from_example)

        if not dry_run:
            example = parse_env(example_path)

    # Synchronize the example with EACH existing environment file.
    for env in existing_envs:
        env_keys = set(env.keys)
        missing_in_env = sorted(
            example_keys - env_keys
        )

        if not missing_in_env:
            continue

        actions.append(
            SyncAction(
                env.path,
                "ADD_KEYS_TO_ENV",
                missing_in_env,
            )
        )

        verb = (
            "would add"
            if dry_run
            else "adding"
        )

        print(
            f"  SYNC: {verb} to {env.path.name}: "
            + ", ".join(missing_in_env)
        )

        blocks = []

        for key in missing_in_env:
            if example and key in example.entries:
                blocks.append(example.entries[key].block)
            else:
                blocks.append(f"{key}=")

        append_section(
            root,
            env.path,
            "Variables synchronized from .env.example",
            blocks,
            backup=backup,
            dry_run=dry_run,
        )

    return env_paths, example_path, actions


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

def _parse_existing_envs(
    env_paths: Iterable[Path],
) -> list[EnvFile]:
    return [
        parse_env(path)
        for path in env_paths
        if path.exists()
    ]


def _print_file_key_lists(
    title: str,
    items: dict[str, list[str]],
) -> None:
    non_empty = {
        name: keys
        for name, keys in items.items()
        if keys
    }

    if not non_empty:
        return

    print(f"  {title}:")

    for name, keys in sorted(non_empty.items()):
        print(f"    {name}:")

        for key in keys:
            print(f"      - {key}")


def audit(
    root: Path,
    *,
    sync: bool,
    backup: bool,
    dry_run: bool,
    strict_unused: bool,
    show_usage: bool,
) -> int:
    failures = 0
    config = load_audit_config(root)
    projects = discover_projects(root, config)

    if not projects:
        print(
            "No .env/.env.* / .env.example files found."
        )
        return 0

    for directory, env_paths, example_path in projects:
        rel = directory.relative_to(root)

        project_label = (
            "."
            if str(rel) == "."
            else rel.as_posix()
        )

        print(f"\n[{project_label}]")

        if env_paths:
            print(
                "  Environment files: "
                + ", ".join(path.name for path in env_paths)
            )

        planned_actions: list[SyncAction] = []

        if sync:
            (
                env_paths,
                example_path,
                planned_actions,
            ) = sync_project(
                root,
                directory,
                env_paths,
                example_path,
                config,
                backup=backup,
                dry_run=dry_run,
            )

        envs = _parse_existing_envs(env_paths)

        example = (
            parse_env(example_path)
            if example_path and example_path.exists()
            else None
        )

        # Current real view.
        env_key_sets = {
            env.path.name: set(env.keys)
            for env in envs
        }

        example_keys = (
            set(example.keys)
            if example
            else set()
        )

        # Virtual view for --dry-run, incorporating the planned actions.
        virtual_env_key_sets = {
            name: set(keys)
            for name, keys in env_key_sets.items()
        }
        virtual_example_keys = set(example_keys)

        if sync and dry_run:
            for action in planned_actions:
                if action.kind == "CREATE_EXAMPLE_FROM_ENVS":
                    virtual_example_keys.update(action.keys)

                elif action.kind == "ADD_KEYS_TO_EXAMPLE":
                    virtual_example_keys.update(action.keys)

                elif action.kind == "CREATE_ENV_FROM_EXAMPLE":
                    virtual_env_key_sets.setdefault(
                        action.target.name,
                        set(),
                    ).update(action.keys)

                elif action.kind == "ADD_KEYS_TO_ENV":
                    virtual_env_key_sets.setdefault(
                        action.target.name,
                        set(),
                    ).update(action.keys)

        # Structural absence.
        missing_example = bool(envs) and not (
            example
            or (
                sync
                and dry_run
                and any(
                    action.kind == "CREATE_EXAMPLE_FROM_ENVS"
                    for action in planned_actions
                )
            )
        )

        missing_env = not envs and not (
            sync
            and dry_run
            and any(
                action.kind == "CREATE_ENV_FROM_EXAMPLE"
                for action in planned_actions
            )
        )

        if missing_example:
            print(
                "  ERROR: .env/.env.* file(s) found without a corresponding .env.example."
            )

        if example and missing_env:
            print(
                "  ERROR: .env.example found without any corresponding .env/.env.* files."
            )

        # Parity calculated based on the virtual view during dry-run and the real view in other cases.
        parity_env_sets = (
            virtual_env_key_sets
            if sync and dry_run
            else env_key_sets
        )

        parity_example_keys = (
            virtual_example_keys
            if sync and dry_run
            else example_keys
        )

        union_env_keys = set().union(
            *parity_env_sets.values()
        ) if parity_env_sets else set()

        missing_from_example = sorted(
            union_env_keys - parity_example_keys
        )

        extra_by_env = {
            name: sorted(
                parity_example_keys - keys
            )
            for name, keys in parity_env_sets.items()
        }

        duplicates_by_file: dict[str, list[str]] = {}

        for env in envs:
            if env.duplicates:
                duplicates_by_file[env.path.name] = env.duplicates

        if example and example.duplicates:
            duplicates_by_file[example.path.name] = example.duplicates

        suspicious = (
            suspicious_example_keys(
                example,
                config,
            )
            if example
            else []
        )

        if sync and dry_run and planned_actions:
            if (
                not missing_from_example
                and not any(extra_by_env.values())
                and not missing_example
                and not missing_env
            ):
                print(
                    "  AFTER_SYNC: key parity would be OK across all environments"
                )
            else:
                print_key_list(
                    "AFTER_SYNC_MISSING_FROM_EXAMPLE",
                    missing_from_example,
                )
                _print_file_key_lists(
                    "AFTER_SYNC_EXAMPLE_KEY_MISSING_FROM_ENVIRONMENT",
                    extra_by_env,
                )

        runtime_files = iter_runtime_files(
            directory,
            config,
        )

        # Audit of usage considers the union of all known keys,
        # including those planned in the dry-run.
        supported_keys = sorted(
            union_env_keys | parity_example_keys
        )

        print(
            f"  Audit of usage: "
            f"{len(supported_keys)} variables, "
            f"{len(runtime_files)} runtime/configuration files",
            flush=True,
        )

        usage_started_at = time.perf_counter()

        evidence = analyze_usage(
            supported_keys,
            runtime_files,
            progress=True,
        )

        usage_elapsed = (
            time.perf_counter()
            - usage_started_at
        )

        print(
            f"  Audit of usage completed in "
            f"{usage_elapsed:.2f}s",
            flush=True,
        )

        weak_usage_only, unused = print_usage_summary(
            evidence,
            root,
            show_usage=show_usage,
        )

        weak_usage_only = [
            key
            for key in weak_usage_only
            if key not in config.ignore_unused_keys
        ]

        unused = [
            key
            for key in unused
            if key not in config.ignore_unused_keys
        ]

        # ---------------------------------------------------------------
        # Automatic removal of variables completely unused.
        #
        # When sync=True:
        # - remove/simulate removal of ALL .env / .env.*;
        # - remove/simulate removal of the .env.example;
        # - show exactly in which files the removal occurred.
        #
        # WEAK_USAGE and ignore_unused_keys are preserved.
        # ---------------------------------------------------------------

        if sync and unused:
            print()

            if dry_run:
                print(
                    "  WOULD AUTOMATICALLY REMOVE the following unused variables "
                    "from all environment files:"
                )
            else:
                print(
                    "  AUTOMATICALLY REMOVING the following unused variables "
                    "from all environment files:"
                )

            for key in unused:
                print(f"    - {key}")

            removed_by_file: dict[str, list[str]] = {}

            for env_path in env_paths:
                if not env_path.exists():
                    continue

                removed = remove_keys_from_env_file(
                    root,
                    env_path,
                    unused,
                    backup=backup,
                    dry_run=dry_run,
                )

                if removed:
                    removed_by_file[env_path.name] = removed

            if example_path and example_path.exists():
                removed = remove_keys_from_env_file(
                    root,
                    example_path,
                    unused,
                    backup=backup,
                    dry_run=dry_run,
                )

                if removed:
                    removed_by_file[example_path.name] = removed

            if removed_by_file:
                print()

                if dry_run:
                    print("  DRY-RUN - removals by file:")
                else:
                    print("  REMOVED BY FILE:")

                for filename, keys in sorted(
                    removed_by_file.items()
                ):
                    print(f"    {filename}:")

                    for key in keys:
                        print(f"      - {key}")

            if not dry_run:
                removed_union = sorted(
                    {
                        key
                        for keys in removed_by_file.values()
                        for key in keys
                    }
                )

                if removed_union:
                    print()
                    print(
                        f"  AUDIT COMPLETE: "
                        f"{len(removed_union)} variable(s) removed."
                    )

                # Re-read all files to reflect the final real state.
                envs = _parse_existing_envs(env_paths)

                example = (
                    parse_env(example_path)
                    if example_path and example_path.exists()
                    else None
                )

                env_key_sets = {
                    env.path.name: set(env.keys)
                    for env in envs
                }

                example_keys = (
                    set(example.keys)
                    if example
                    else set()
                )

                union_env_keys = set().union(
                    *env_key_sets.values()
                ) if env_key_sets else set()

                missing_from_example = sorted(
                    union_env_keys - example_keys
                )

                extra_by_env = {
                    name: sorted(
                        example_keys - keys
                    )
                    for name, keys in env_key_sets.items()
                }

                duplicates_by_file = {}

                for env in envs:
                    if env.duplicates:
                        duplicates_by_file[
                            env.path.name
                        ] = env.duplicates

                if example and example.duplicates:
                    duplicates_by_file[
                        example.path.name
                    ] = example.duplicates

                suspicious = (
                    suspicious_example_keys(
                        example,
                        config,
                    )
                    if example
                    else []
                )

                unused = [
                    key
                    for key in unused
                    if key not in removed_union
                ]

        print_key_list(
            "MISSING_FROM_EXAMPLE",
            missing_from_example,
        )

        _print_file_key_lists(
            "EXAMPLE_KEY_MISSING_FROM_ENVIRONMENT",
            extra_by_env,
        )

        _print_file_key_lists(
            "DUPLICATE_KEYS",
            duplicates_by_file,
        )

        print_key_list(
            "POSSIBLE_SECRET_IN_EXAMPLE",
            suspicious,
        )

        print_key_list(
            "WEAK_USAGE_ONLY",
            weak_usage_only,
        )

        print_key_list(
            "POSSIBLY_UNUSED",
            unused,
        )

        structural_failure = (
            missing_example
            or (example is not None and missing_env)
            or bool(missing_from_example)
            or any(extra_by_env.values())
            or bool(duplicates_by_file)
            or bool(suspicious)
        )

        if not any(
            [
                structural_failure,
                weak_usage_only,
                unused,
            ]
        ):
            print("  OK")

        if structural_failure:
            failures += 1

        elif strict_unused and unused:
            failures += 1

    return failures


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
    )

    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Workspace/project root.",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Returns exit code 1 when .env/.env.* and .env.example differ, "
            "duplicate keys exist, or a possible secret is found in the example file."
        ),
    )

    parser.add_argument(
        "--strict-unused",
        action="store_true",
        help=(
            "With --strict, also fails if a variable has no detected references."
        ),
    )

    parser.add_argument(
        "--audit-only",
        action="store_true",
        help=(
            "Audits only; does not synchronize or remove variables."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Simulates synchronization and automatic removals without writing files."
        ),
    )

    parser.add_argument(
        "--no-backup",
        action="store_true",
        help=(
            "Does not create backups before modifying existing files."
        ),
    )

    parser.add_argument(
        "--show-usage",
        action="store_true",
        help=(
            "Shows files where each variable has strong or weak usage evidence."
        ),
    )

    args = parser.parse_args()

    if args.strict_unused and not args.strict:
        parser.error(
            "--strict-unused must be used together with --strict"
        )

    if args.audit_only and args.dry_run:
        parser.error(
            "--audit-only and --dry-run are incompatible modes"
        )

    root = Path(args.root).resolve()

    mode = (
        "AUDIT ONLY"
        if args.audit_only
        else "DRY RUN"
        if args.dry_run
        else "SYNCHRONIZATION + AUDIT + AUTOMATIC CLEANUP"
    )

    print("=" * 72)
    print("ENV AUDITOR")
    print(f"Mode: {mode}")

    if args.audit_only:
        print(
            "No files will be modified."
        )
        print(
            "Unused variables will only be reported."
        )

    elif args.dry_run:
        print(
            "No files will be modified; synchronization and removals "
            "will only be simulated."
        )
        print(
            "Completely unused variables would be automatically removed "
            "from all .env / .env.* files and .env.example."
        )

    else:
        print(
            "All .env / .env.* files will be synchronized with .env.example."
        )
        print(
            "Completely unused variables will be automatically removed "
            "from all .env / .env.* files and .env.example."
        )
        print(
            "Variables with weak usage evidence only will be preserved."
        )
        print(
            "Backups: "
            + (
                "disabled"
                if args.no_backup
                else "enabled"
            )
        )

    print("=" * 72)

    try:
        failures = audit(
            root,
            sync=not args.audit_only,
            backup=not args.no_backup,
            dry_run=args.dry_run,
            strict_unused=args.strict_unused,
            show_usage=args.show_usage,
        )
    except RuntimeError as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        return 2

    print("\n" + "=" * 72)

    if failures:
        print(
            f"Completed with {failures} project(s) still requiring review."
        )
    else:
        print(
            "Completed: key parity and structural validations have no outstanding issues."
        )

    print("=" * 72)

    return 1 if args.strict and failures else 0


if __name__ == "__main__":
    sys.exit(main())
