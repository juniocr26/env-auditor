import contextlib
import importlib.util
import io
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'audit-envs.py'
spec = importlib.util.spec_from_file_location('audit_envs', SCRIPT)
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


class AuditorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode())
        return path

    def run_audit(self, preview=False):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = audit.run(self.root, preview)
        return code, output.getvalue()

    def snapshot(self):
        return {str(p.relative_to(self.root)): (p.read_bytes(), stat.S_IMODE(p.stat().st_mode))
                for p in self.root.rglob('*') if p.is_file()}

    def test_actual_layout_default_and_all_caller_directories(self):
        self.assertEqual(audit.resolve_root(), SCRIPT.parents[2])
        # Copy into the same scripts layout; CLI checks never touch real targets.
        script = self.put('workspace/env-auditor/scripts/audit-envs.py', SCRIPT.read_bytes())
        self.put('workspace/sibling/.env.example', 'A=literal\n')
        workspace = self.root / 'workspace'
        for cwd in (workspace, script.parents[1], script.parent):
            result = subprocess.run([sys.executable, '-B', str(script), '--dry-run'], cwd=cwd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(f'Scan root: {workspace}', result.stdout)
            self.assertIn('sibling/.env', result.stdout)
        self.assertFalse((workspace / 'sibling/.env').exists())

    def test_root_overrides_and_invalid_roots(self):
        self.assertEqual(audit.resolve_root(str(self.root)), self.root)
        previous = Path.cwd()
        try:
            os.chdir(self.root.parent)
            self.assertEqual(audit.resolve_root(self.root.name), self.root)
        finally:
            os.chdir(previous)
        for root in (self.root / 'missing', self.put('file', 'x')):
            with self.assertRaises(audit.InputError):
                audit.resolve_root(str(root))

    def test_recursive_hidden_ignored_and_excluded_discovery(self):
        expected = [self.put(n, 'A=x') for n in ('sibling/.env', 'other/nested/.env.prod', '.hidden/.env.example', 'ignored/.env')]
        self.put('.gitignore', 'ignored/\n')
        for name in audit.EXCLUDED:
            self.put(name + '/.env', 'A=x')
        for name in ('bootstrap/cache', 'public/build'):
            self.put('nested/' + name + '/.env', 'A=x')
        for name in ('.env.bak', '.env.prod.bak.old', '.env~', '.env.prod~'):
            self.put(name, 'A=x')
        groups, errors, links = audit.discover(self.root)
        self.assertEqual({p for paths in groups.values() for p in paths}, set(expected))
        self.assertFalse(errors or links)

    def test_symbolic_files_and_directories_not_followed(self):
        source = self.put('actual/.env.example', 'A=x')
        (self.root / 'linked').symlink_to(source.parent, target_is_directory=True)
        (self.root / '.env.example').symlink_to(source)
        (self.root / '.env').symlink_to(self.root / 'missing')
        with tempfile.TemporaryDirectory() as outside:
            Path(outside, '.env').write_text('SECRET=x')
            (self.root / 'outside').symlink_to(outside, target_is_directory=True)
            groups, errors, links = audit.discover(self.root)
        self.assertEqual(len(links), 4)
        self.assertEqual(sum(map(len, groups.values())), 1)
        self.assertFalse(errors)
        self.assertEqual(self.run_audit()[0], 0)
        self.assertTrue((self.root / '.env').is_symlink())

    def test_authoritative_pairs_variants_and_creation(self):
        self.put('p/.env.example', '# referência\nA=$(literal)\n')
        self.put('p/.env.local', 'A=\nOLD=secret\n')
        self.put('p/.env.prod.example', 'PROD="${NO_EXPANSION}"\n')
        self.put('p/.env.prod', 'A=old\n')
        self.put('orphan/.env', 'KEEP=secret\n')
        self.put('p/.env.odd.example.example', 'X=x\n')
        before_examples = {p: p.read_bytes() for p in self.root.rglob('*.example')}
        code, output = self.run_audit()
        self.assertEqual(code, 0, output)
        self.assertEqual((self.root / 'p/.env').read_bytes(), before_examples[self.root / 'p/.env.example'])
        self.assertEqual((self.root / 'p/.env.local').read_text(), 'A=\n')
        self.assertEqual((self.root / 'p/.env.prod').read_text(), 'PROD="${NO_EXPANSION}"\n')
        self.assertEqual((self.root / 'orphan/.env').read_text(), 'KEEP=secret\n')
        self.assertFalse((self.root / 'p/.env.test').exists())
        self.assertFalse((self.root / 'p/.env.odd.example').exists())
        for path, data in before_examples.items():
            self.assertEqual(path.read_bytes(), data)
        self.assertEqual(stat.S_IMODE((self.root / 'p/.env').stat().st_mode), 0o600)

    def test_literal_blocks_preservation_backups_permissions_idempotency(self):
        original = b'# keep\r\nA=\r\nA=second\r\nMULTI="first\r\nsecond" # end\r\nOLD=\'one\r\ntwo\'\r\n# tail'
        target = self.put('nested/p/.env', original)
        target.chmod(0o640)
        self.put('nested/p/.env.example', 'A=default\nMULTI="different"\nNEW=\'á\n${literal}\'\n')
        code, output = self.run_audit()
        self.assertEqual(code, 0, output)
        self.assertEqual(target.read_bytes(), b'# keep\r\nA=\r\nA=second\r\nMULTI="first\r\nsecond" # end\r\n# tail\n' + "NEW='á\n${literal}'\n".encode())
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)
        backups = self.root / '.env-audit-backups'
        saved = list(backups.rglob('*.original'))
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].read_bytes(), original)
        self.assertEqual(saved[0].with_name('.env.removed').read_bytes(), b"OLD='one\r\ntwo'\r\n")
        self.assertEqual(saved[0].relative_to(backups).parts[1:], ('nested', 'p', '.env.original'))
        self.assertIn('Z-', saved[0].relative_to(backups).parts[0])
        for path in backups.rglob('*'):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700 if path.is_dir() else 0o600)
        self.assertEqual(stat.S_IMODE(backups.stat().st_mode), 0o700)
        self.assertEqual((backups / '.gitignore').read_bytes(), b'*\n')
        before = self.snapshot()
        self.assertEqual(self.run_audit()[0], 0)
        self.assertEqual(self.snapshot(), before)
        self.assertIn('unchanged=1', self.run_audit()[1])

    def test_invalid_examples_leave_targets_unchanged_and_continue(self):
        for index, data in enumerate((b'A=1\nA=2\n', b'A="unterminated\n', b'not an assignment\n', b'X=\xff', b'A="ok" garbage\n', b'A=\x00')):
            self.put(f'bad{index}/.env.example', data)
            self.put(f'bad{index}/.env', 'KEEP=secret_fixture_837\n')
        self.put('good/.env.example', 'OK=yes\n')
        code, output = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn('errors=6', output)
        self.assertNotIn('secret_fixture_837', output)
        for index in range(6):
            self.assertEqual((self.root / f'bad{index}/.env').read_text(), 'KEEP=secret_fixture_837\n')
        self.assertEqual((self.root / 'good/.env').read_text(), 'OK=yes\n')

    def test_empty_examples_and_duplicate_targets(self):
        self.put('empty/.env.example', '')
        self.put('empty/.env', '# comment\nA=1\nA=2\n')
        self.put('new/.env.example', '')
        self.assertEqual(self.run_audit()[0], 0)
        self.assertEqual((self.root / 'empty/.env').read_text(), '# comment\n')
        self.assertEqual((self.root / 'new/.env').read_bytes(), b'')

    def test_unreadable_reference_or_target_injected_even_as_root(self):
        reference = self.put('.env.example', 'A=x\n')
        target = self.put('.env', 'A=secret\nOLD=x\n')
        original = target.read_bytes()
        real_read = Path.read_bytes
        for blocked in (reference, target):
            def failing_read(path):
                if path == blocked:
                    raise PermissionError('secret must never appear')
                return real_read(path)
            with patch.object(Path, 'read_bytes', failing_read):
                code, output = self.run_audit()
            self.assertEqual(code, 1)
            self.assertNotIn('secret', output)
            self.assertEqual(target.read_bytes(), original)
        self.assertFalse((self.root / '.env-audit-backups').exists())

    def test_malformed_target_unchanged(self):
        self.put('.env.example', 'A=x\n')
        target = self.put('.env', 'A="unclosed')
        self.assertEqual(self.run_audit()[0], 1)
        self.assertEqual(target.read_text(), 'A="unclosed')

    def test_backup_failure_prevents_write_and_other_pairs_continue(self):
        target = self.put('bad/.env', 'OLD=secret_fixture_837\n')
        self.put('bad/.env.example', 'A=x\n')
        self.put('good/.env.example', 'B=x\n')
        with patch.object(audit, 'private_file', side_effect=PermissionError('secret_fixture_837')):
            code, output = self.run_audit()
        self.assertEqual(code, 1)
        self.assertEqual(target.read_text(), 'OLD=secret_fixture_837\n')
        self.assertEqual((self.root / 'good/.env').read_text(), 'B=x\n')
        self.assertNotIn('secret_fixture_837', output)

    def test_removed_backup_failure_prevents_modification(self):
        target = self.put('.env', 'OLD=x\n')
        self.put('.env.example', 'A=x\n')
        actual = audit.private_file
        def fail_removed(path, data):
            if path.name.endswith('.removed'):
                raise PermissionError()
            return actual(path, data)
        with patch.object(audit, 'private_file', side_effect=fail_removed):
            self.assertEqual(self.run_audit()[0], 1)
        self.assertEqual(target.read_text(), 'OLD=x\n')
        self.assertEqual(len(list(self.root.rglob('*.original'))), 1)

    def test_discovery_failure_is_nonzero_not_empty_success(self):
        actual = audit.os.scandir
        self.put('bad/.env', 'A=x')
        self.put('good/.env.example', 'A=x')
        def denied(path):
            if Path(path).name == 'bad':
                raise PermissionError('secret')
            return actual(path)
        with patch.object(audit.os, 'scandir', side_effect=denied):
            code, output = self.run_audit()
        self.assertEqual(code, 1)
        self.assertNotIn('No environment files found', output)
        self.assertNotIn('secret', output)
        self.assertTrue((self.root / 'good/.env').exists())
        with patch.object(audit.os, 'scandir', side_effect=PermissionError()):
            code, output = self.run_audit()
        self.assertEqual(code, 1)
        self.assertNotIn('No environment files found', output)

    def test_preview_modes_write_nothing(self):
        self.put('update/.env', 'OLD=x\n')
        self.put('update/.env.example', 'A=x\n')
        self.put('create/.env.example', 'B=x\n')
        before = self.snapshot()
        dirs = set(self.root.rglob('*'))
        for flag in ('--dry-run', '--audit-only'):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(audit.main([str(self.root), flag]), 0)
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(set(self.root.rglob('*')), dirs)

    def test_atomic_failure_cleans_temporary_and_preserves_target(self):
        target = self.put('.env', 'OLD=x\n')
        self.put('.env.example', 'A=x\n')
        with patch.object(audit.os, 'replace', side_effect=PermissionError()):
            self.assertEqual(self.run_audit()[0], 1)
        self.assertEqual(target.read_text(), 'OLD=x\n')
        self.assertFalse(list(self.root.glob('.audit-env-*')))
        self.assertEqual(len(list(self.root.rglob('*.original'))), 1)

    def test_collision_safe_backup_and_symbolic_backup_rejection(self):
        target = self.put('.env', 'A=x\n')
        first = audit.backup(self.root, target, b'A=x\n', b'')
        second = audit.backup(self.root, target, b'A=x\n', b'')
        self.assertNotEqual(first, second)
        with tempfile.TemporaryDirectory() as other:
            root = Path(other)
            (root / '.env-audit-backups').symlink_to(self.root)
            with self.assertRaises(audit.InputError):
                audit.backup(root, root / '.env', b'', b'')

    def test_complete_tables_order_alignment_and_project_summary(self):
        self.put('demo/config/.env', 'Z_SHARED=secret_fixture_837\nB_OLD=x\nA_OLD=x\n')
        self.put('demo/config/.env.example', 'Z_SHARED=default\nB_NEW=x\nA_NEW=x\n')
        self.put('demo/.env.prod.example', 'PROD=x\n')
        self.put('clean/.env', 'KEEP=\n')
        self.put('clean/.env.example', 'KEEP=default\n')
        code, output = self.run_audit(True)
        self.assertEqual(code, 0)
        complete, summary = output.split('Resumo final por projeto (comparação inicial)')
        rows = [line for line in complete.splitlines() if line.startswith('│') and any(k in line for k in ('A_NEW', 'B_NEW', 'A_OLD', 'B_OLD', 'Z_SHARED'))]
        self.assertEqual([line.split('│')[1].strip() for line in rows], ['A_NEW', 'B_NEW', 'A_OLD', 'B_OLD', 'Z_SHARED'])
        self.assertEqual(len({len(line) for line in rows}), 1)
        self.assertEqual(len({tuple(i for i, char in enumerate(line) if char == '│') for line in rows}), 1)
        for glyph in '┌┬┐├┼┤└┴┘│─':
            self.assertIn(glyph, complete)
        self.assertNotIn('Z_SHARED', summary)
        self.assertNotIn('KEEP', summary)
        self.assertIn('Projeto: demo', summary)
        self.assertNotIn('Projeto: demo/config', summary)
        self.assertIn('Alvo: demo/config/.env', summary)
        self.assertIn('Referência: demo/.env.prod.example', summary)
        self.assertIn('Somente no .env.prod.example', complete)
        self.assertIn('Adicionar ao .env.prod', complete)
        self.assertIn('Nenhuma pendência de sincronização.', summary)
        self.assertIn('Proposta: Remover do .env', summary)
        self.assertIn('Alvo ausente', complete)
        self.assertIn('shared=2', summary)
        self.assertIn('actual_updated=0', summary)
        self.assertNotIn('secret_fixture_837', output)

    def test_summary_completed_failed_and_unapplied_initial_counts(self):
        target = self.put('demo/.env', 'OLD=secret_fixture_837\nKEEP=\n')
        self.put('demo/.env.example', 'NEW=default\nKEEP=default\n')
        before = self.snapshot()
        with patch.object(audit.os, 'replace', side_effect=PermissionError('secret_fixture_837')):
            code, output = self.run_audit()
        summary = output.split('Resumo final por projeto (comparação inicial)')[1]
        self.assertEqual(code, 1)
        self.assertIn('Não aplicada: Adicionar ao .env', summary)
        self.assertIn('Falhou: sincronizar par', summary)
        self.assertNotIn('Concluída:', summary)
        self.assertIn('added=1, removed=1, shared=1', summary)
        self.assertIn('actual_updated=0', summary)
        self.assertEqual(target.read_bytes(), before['demo/.env'][0])
        code, output = self.run_audit()
        self.assertEqual(code, 0)
        summary = output.split('Resumo final por projeto (comparação inicial)')[1]
        self.assertIn('Concluída: Remover do .env', summary)
        self.assertIn('actual_updated=1', summary)
        self.assertIn('Modo de execução: sincronização com backup', summary)
        self.assertEqual(target.read_text(), 'KEEP=\nNEW=default\n')
        self.assertNotIn('secret_fixture_837', output)

    def test_missing_empty_target_reference_and_parse_findings(self):
        self.put('empty/.env.example', '')
        self.put('orphan/.env', 'KEEP=secret_fixture_837\n')
        self.put('bad/.env.example', 'invalid secret_fixture_837')
        code, output = self.run_audit(True)
        self.assertEqual(code, 1)
        summary = output.split('Resumo final por projeto (comparação inicial)')[1]
        self.assertIn('Proposta: Criar .env', summary)
        self.assertIn('Referência ausente', summary)
        self.assertIn('Falhou: validar entradas', summary)
        self.assertNotIn('secret_fixture_837', output)
        self.assertFalse((self.root / 'empty/.env').exists())
        self.assertFalse((self.root / '.env-audit-backups').exists())

    def test_unicode_filename_table_display_alignment(self):
        self.put('demo/.env.生产', 'OLD=x\nKEEP=\n')
        self.put('demo/.env.生产.example', 'NEW=x\nKEEP=x\n')
        code, output = self.run_audit(True)
        self.assertEqual(code, 0)
        complete = output.split('Resumo final por projeto (comparação inicial)')[0]
        lines = [line for line in complete.splitlines() if line.startswith(('│', '┌', '├', '└'))]
        self.assertEqual(len({audit.display_width(line) for line in lines}), 1)

    def test_empty_creation_failure_and_discovery_summary(self):
        self.put('demo/.env.example', '')
        with patch.object(audit.os, 'replace', side_effect=PermissionError()):
            code, output = self.run_audit()
        self.assertEqual(code, 1)
        summary = output.split('Resumo final por projeto (comparação inicial)')[1]
        self.assertIn('Não aplicada: Criar .env', summary)
        self.assertIn('Falhou: sincronizar par', summary)
        self.assertNotIn('Falhou: validar entradas', summary)
        self.assertFalse((self.root / 'demo/.env').exists())
        with patch.object(audit.os, 'scandir', side_effect=PermissionError()):
            code, output = self.run_audit(True)
        self.assertEqual(code, 1)
        self.assertIn('Falhou: descobrir arquivos', output.split('Resumo final por projeto (comparação inicial)')[1])

    def test_retired_options_rejected_and_settings_ignored(self):
        for option in ('--strict', '--strict-unused', '--show-usage', '--no-backup'):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
                audit.main([str(self.root), option])
            self.assertEqual(result.exception.code, 2)
        self.put('.env-audit.json', '{not valid JSON')
        self.put('.env.example', 'A=x\n')
        self.assertEqual(self.run_audit()[0], 0)
        self.assertEqual((self.root / '.env').read_text(), 'A=x\n')


if __name__ == '__main__':
    unittest.main()
