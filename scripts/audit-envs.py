#!/usr/bin/env python3
"""Synchronize literal environment assignments using authoritative examples."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import unicodedata

EXCLUDED = set('''.git .hg .svn node_modules vendor __pycache__ .venv venv
.env-audit-backups backups backup dist build out target .next .nuxt .cache
coverage .pytest_cache .tox'''.split())
ASSIGNMENT = re.compile(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=')


class InputError(Exception):
    """Safe diagnostic: never contains input values."""


@dataclass
class Document:
    raw: bytes
    blocks: list[tuple[str | None, str]]

    @property
    def keys(self):
        return [key for key, _ in self.blocks if key is not None]


def parse(raw: bytes) -> Document:
    try:
        text = raw.decode('utf-8')
    except UnicodeError:
        raise InputError('invalid UTF-8') from None
    if '\x00' in text:
        raise InputError('NUL byte in input')
    lines = text.splitlines(keepends=True)
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith('#'):
            blocks.append((None, line))
            continue
        match = ASSIGNMENT.match(line)
        if not match:
            raise InputError(f'malformed assignment at line {i}')
        value = line[match.end():].lstrip()
        block = line
        if value.startswith(('"', "'")):
            quote = value[0]
            content = value[1:]
            escaped = False
            while True:
                closed = False
                for index, char in enumerate(content):
                    if escaped:
                        escaped = False
                    elif char == '\\':
                        escaped = True
                    elif char == quote:
                        tail = content[index + 1:].strip()
                        if tail and not tail.startswith('#'):
                            raise InputError(f'invalid quoted assignment near line {i}')
                        closed = True
                        break
                if closed:
                    break
                if i == len(lines):
                    raise InputError('unterminated quoted assignment')
                content = lines[i]
                block += content
                i += 1
        blocks.append((match.group(1), block))
    return Document(raw, blocks)


def read_document(path: Path) -> Document:
    # Reject links again at processing time, including dangling links.
    if not stat.S_ISREG(path.lstat().st_mode):
        raise InputError('input is not a regular file')
    return parse(path.read_bytes())


def eligible(name: str) -> bool:
    return (name == '.env' or name.startswith('.env.')) and '.bak' not in name and not name.endswith('~')


def discover(root: Path):
    groups: dict[Path, list[Path]] = {}
    errors = []
    skipped = []

    def walk(directory):
        try:
            with os.scandir(directory) as entries:
                for entry in sorted(entries, key=lambda e: e.name):
                    path = Path(entry.path)
                    try:
                        if entry.is_symlink():
                            skipped.append(path)
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name not in EXCLUDED and path.parts[-2:] not in [('bootstrap', 'cache'), ('public', 'build')]:
                                walk(path)
                        elif eligible(entry.name):
                            if entry.is_file(follow_symlinks=False):
                                groups.setdefault(directory, []).append(path)
                            else:
                                errors.append(path)
                    except OSError:
                        errors.append(path)
        except OSError:
            errors.append(directory)
    walk(root)
    return groups, errors, skipped


def plan(target: Document, example: Document):
    counts = Counter(example.keys)
    if any(count > 1 for count in counts.values()):
        raise InputError('duplicate keys in example')
    allowed = set(example.keys)
    existing = set(target.keys)
    added = [key for key in example.keys if key not in existing]
    removed = sorted(existing - allowed)
    result = ''.join(block for key, block in target.blocks if key is None or key in allowed)
    removed_bytes = ''.join(block for key, block in target.blocks if key is not None and key not in allowed).encode('utf-8')
    for key, block in example.blocks:
        if key in added:
            if result and not result.endswith(('\n', '\r')):
                result += '\n'
            result += block
    return result.encode('utf-8'), removed_bytes, added, removed


def secure_directory(path: Path):
    if path.is_symlink():
        raise InputError('symbolic backup directory')
    path.mkdir(mode=0o700, exist_ok=True)
    os.chmod(path, 0o700)


def private_file(path: Path, data: bytes):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)


def backup(root: Path, target: Path, original: bytes, removed: bytes):
    base = root / '.env-audit-backups'
    secure_directory(base)
    ignore = base / '.gitignore'
    if ignore.is_symlink():
        raise InputError('symbolic backup ignore file')
    if not ignore.exists():
        private_file(ignore, b'*\n')
    elif ignore.read_bytes() != b'*\n':
        raise InputError('backup ignore file must contain only *')
    os.chmod(ignore, 0o600)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-')
    session = Path(tempfile.mkdtemp(prefix=stamp, dir=base))
    folder = session
    for part in target.relative_to(root).parent.parts:
        folder /= part
        secure_directory(folder)
    original_path = folder / (target.name + '.original')
    removed_path = folder / (target.name + '.removed')
    private_file(original_path, original)
    private_file(removed_path, removed)
    return original_path, removed_path


def atomic_write(path: Path, data: bytes, mode: int):
    fd, temporary = tempfile.mkstemp(prefix='.audit-env-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def resolve_root(override=None):
    root = Path(override).resolve() if override is not None else Path(__file__).resolve().parents[2]
    if not root.is_dir():
        raise InputError('scan root does not exist or is not a directory')
    return root


def display_width(text):
    return sum(0 if unicodedata.combining(char) else 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1
               for char in text)


def table(rows):
    """Render identifier-only rows; input values never enter the presentation."""
    headers = ('Variável', 'Situação', 'Ação prevista')
    widths = [max(display_width(row[i]) for row in [headers, *rows]) for i in range(3)]

    def border(left, join, right):
        return left + join.join('─' * (width + 2) for width in widths) + right

    def line(row):
        return '│' + '│'.join(' ' + cell + ' ' * (width - display_width(cell) + 1)
                             for cell, width in zip(row, widths)) + '│'

    print(border('┌', '┬', '┐'))
    print(line(headers))
    for row in rows:
        print(border('├', '┼', '┤'))
        print(line(row))
    print(border('└', '┴', '┘'))


def comparison_rows(target, example, added, removed, shared):
    return ([(key, f'Somente no {example.name}', f'Adicionar ao {target.name}') for key in sorted(added)]
            + [(key, f'Somente no {target.name}', f'Remover do {target.name}') for key in sorted(removed)]
            + [(key, 'Presente nos dois', f'Preservar valor do {target.name}') for key in sorted(shared)])


def project_name(root, directory):
    relative = directory.relative_to(root)
    return relative.parts[0] if relative.parts else '.'


def pair_heading(root, target, example):
    print(f'Alvo: {target.relative_to(root)}')
    print(f'Referência: {example.relative_to(root)}' if example else 'Referência: ausente')


def run(root: Path, preview=False) -> int:
    print(f'Scan root: {root}')
    totals = Counter(created=0, updated=0, unchanged=0, skipped=0, errors=0, added=0, removed=0)
    summaries = {}
    findings = {}
    mode = 'auditoria' if preview else 'sincronização com backup'
    print(f'Modo: {mode}')
    totals.update(shared=0, actual_created=0, actual_updated=0)
    groups, errors, links = discover(root)
    for path in links:
        print(f'Skipped symbolic link: {path.relative_to(root)}')
        totals['skipped'] += 1
    for path in errors:
        print(f'ERROR: discovery failed: {path.relative_to(root)}')
        project = project_name(root, path.parent if path != root else root)
        findings.setdefault(project, []).append(('', f'Erro de descoberta: {path.relative_to(root)}', 'Falhou: descobrir arquivos'))
        totals['errors'] += 1
    if not groups and not errors:
        print('No environment files found.')
    if (root / '.env-audit.json').exists():
        print('Retired .env-audit.json settings ignored; remove this file.')
    for directory, paths in sorted(groups.items()):
        project = project_name(root, directory)
        records = summaries.setdefault(project, [])
        print(f'Projeto: {project}')
        print(f'[{directory.relative_to(root)}] Discovered: ' + ', '.join(p.name for p in paths))
        by_name = {p.name: p for p in paths}
        targets = {p.name for p in paths if not p.name.endswith('.example')}
        targets.update(p.name[:-8] for p in paths if p.name.endswith('.example') and not p.name[:-8].endswith('.example'))
        for name in sorted(targets):
            target = directory / name
            example = by_name.get(name + '.example') or by_name.get('.env.example')
            if target.is_symlink() or (target.exists() and not target.is_file()):
                print(f'Skipped {target.relative_to(root)}: symbolic or nonregular target')
                records.append((target, example, [('', 'Alvo simbólico ou não regular', 'Não aplicada: verificar alvo')]))
                totals['skipped'] += 1
                continue
            if example is None:
                print(f'Skipped {target.relative_to(root)}: no matching example; unchanged')
                totals['skipped'] += 1
                records.append((target, None, [('', 'Referência ausente', 'Não aplicada: localizar referência')]))
                continue
            print(f'Pair: {target.relative_to(root)} <- {example.relative_to(root)}')
            pair_heading(root, target, example)
            rows = []
            planned = False
            exists = None
            try:
                reference = read_document(example)
                exists = target.exists()
                document = read_document(target) if exists else Document(b'', [])
                data, removed_bytes, added, removed = plan(document, reference)
                # A new target copies the entire validated example, including comments.
                if not exists:
                    data = reference.raw
                planned = True
                outcome = 'created' if not exists else 'updated' if data != document.raw else 'unchanged'
                shared = set(document.keys) & set(reference.keys)
                rows = comparison_rows(target, example, added, removed, shared)
                table(rows)
                if not exists:
                    print('Alvo ausente: criação proposta.' if preview else 'Alvo ausente: criação necessária.')
                totals['added'] += len(added)
                totals['removed'] += len(removed)
                totals['shared'] += len(shared)
                if not preview and outcome != 'unchanged':
                    permissions = stat.S_IMODE(target.stat().st_mode) if exists else 0o600
                    if exists:
                        for saved in backup(root, target, document.raw, removed_bytes):
                            print(f'  Backup: {saved}')
                    atomic_write(target, data, permissions)
                print(f'  {"Proposed " if preview else ""}{outcome}')
                totals[outcome] += 1
                if not preview and outcome != 'unchanged':
                    totals['actual_' + outcome] += 1
                if outcome == 'unchanged':
                    print('Par inalterado.')
                prefix = 'Proposta: ' if preview else 'Concluída: '
                actions = [(key, status, prefix + action) for key, status, action in rows if status != 'Presente nos dois']
                if not exists:
                    actions.append(('', 'Alvo ausente na comparação inicial', prefix + f'Criar {target.name}'))
                records.append((target, example, actions))
            except (OSError, InputError) as exc:
                # OSError messages can contain arbitrary data supplied by mocks or OS.
                reason = str(exc) if isinstance(exc, InputError) else type(exc).__name__
                print(f'ERROR: {target.relative_to(root)}: {reason}; target unchanged')
                totals['errors'] += 1
                totals['skipped'] += 1
                actions = [(key, status, 'Não aplicada: ' + action) for key, status, action in rows if status != 'Presente nos dois']
                if planned and not exists:
                    actions.append(('', 'Alvo ausente na comparação inicial', f'Não aplicada: Criar {target.name}'))
                actions.append(('', 'Falha: ' + reason, 'Falhou: sincronizar par' if planned else 'Falhou: validar entradas'))
                records.append((target, example, actions))
    print('Resumo final por projeto (comparação inicial)')
    for project in sorted(summaries.keys() | findings.keys()):
        records = summaries.get(project, [])
        print(f'Projeto: {project}')
        if findings.get(project):
            table(findings[project])
        if not findings.get(project) and not any(actions for _, _, actions in records):
            print('Nenhuma pendência de sincronização.')
        for target, example, actions in records:
            if actions:
                pair_heading(root, target, example)
                table(actions)
    if preview:
        print('Ações propostas; nenhum arquivo foi alterado. Nenhum backup foi criado.')
    print(f'Modo de execução: {mode}')
    print(('Proposed totals: ' if preview else 'Totals: ') + ', '.join(f'{k}={v}' for k, v in totals.items()))
    return 1 if totals['errors'] else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', help='Scan root (relative to caller when supplied)')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--dry-run', action='store_true', help='Calculate changes without writes')
    modes.add_argument('--audit-only', action='store_true', help='Calculate changes without writes')
    args = parser.parse_args(argv)
    try:
        root = resolve_root(args.root)
    except (OSError, RuntimeError, InputError):
        print('ERROR: invalid scan root (must be an accessible directory)', file=sys.stderr)
        return 2
    return run(root, args.dry_run or args.audit_only)


if __name__ == '__main__':
    sys.exit(main())
