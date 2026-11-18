import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import storage_guard as g


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('STORAGE_GUARD_TEST_TEMP'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'block'

    def test_reject_parent_and_outside(self):
        for path in (self.root, self.root.parent / 'other', self.output / 'nested'):
            with self.assertRaises(RuntimeError):
                g.validate_output(path, self.root)

    def test_resume_is_explicit(self):
        self.output.mkdir()
        with self.assertRaises(RuntimeError):
            g.validate_output(self.output, self.root)
        self.assertEqual(g.validate_output(self.output, self.root, True), self.output.resolve())

    def test_free_space_reserves_peak_allocation(self):
        # D: must retain 15 GiB *after* the planned 2 GiB allocation.
        with patch.object(g, 'space_status', return_value=[dict(Volume='D:/', FreeBytes=16*g.GIB, FreeGiB=16, ReserveGiB=15)]):
            with self.assertRaisesRegex(RuntimeError, '17.00 GiB'):
                g.require_space(Path('D:/knx_analysis/workflow-scratch/test'), 2*g.GIB)

    def test_preflight_refuses_before_child(self):
        with patch.object(g, 'require_space', side_effect=RuntimeError('low disk')), patch.object(g.subprocess, 'Popen') as start:
            with self.assertRaisesRegex(RuntimeError, 'low disk'):
                g.run_bounded(['unused'], self.output, 100, scratch=self.root)
            start.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_single_owner_lock_is_not_stolen(self):
        registry = self.root / '.storage'
        registry.mkdir()
        lock = registry / 'active.lock'
        lock.write_text('other owner')
        with patch.object(g, 'require_space'), patch.object(g.subprocess, 'Popen') as start:
            with self.assertRaises(FileExistsError):
                g.run_bounded(['unused'], self.output, 100, scratch=self.root)
            start.assert_not_called()
        self.assertEqual(lock.read_text(), 'other owner')

    def test_budget_stops_only_owned_writer_and_keeps_evidence(self):
        code = 'from pathlib import Path; import sys,time; p=Path(sys.argv[1]); p.mkdir(); (p/"data").write_bytes(b"x"*4096); time.sleep(30)'
        with patch.object(g, 'require_space'):
            with self.assertRaisesRegex(RuntimeError, 'budget exceeded'):
                g.run_bounded([sys.executable, '-c', code, str(self.output)], self.output, 1024,
                              scratch=self.root, interval=0.05)
        self.assertEqual((self.output/'data').stat().st_size, 4096)
        self.assertFalse((self.root/'.storage/active.lock').exists())
        receipt = json.loads(next((self.root/'.storage').glob('*.json')).read_text())
        self.assertEqual(receipt['Status'], 'stopped')

    def test_child_exit_code_is_preserved(self):
        with patch.object(g, 'require_space'):
            self.assertEqual(g.run_bounded([sys.executable, '-c', 'raise SystemExit(7)'],
                                          self.output, 1024, scratch=self.root, interval=0.05), 7)

    def test_current_output_over_budget_never_starts(self):
        self.output.mkdir()
        (self.output/'original').write_bytes(b'x'*100)
        with patch.object(g.subprocess, 'Popen') as start:
            with self.assertRaisesRegex(RuntimeError, 'already exceeds'):
                g.run_bounded(['unused'], self.output, 10, resume=True, scratch=self.root)
            start.assert_not_called()

    def receipt(self):
        return json.loads(next((self.root/'.storage').glob('*.json')).read_text())

    @staticmethod
    def healthy_space():
        return [dict(Volume=volume, FreeBytes=100*g.GIB, FreeGiB=100, ReserveGiB=reserve)
                for volume, reserve in [('C:/', 10), ('D:/', 15)]]

    def test_advisory_actual_child_overrun_finishes_and_preserves_environment(self):
        code = ('import os,sys,time; from pathlib import Path; '
                'p=Path(sys.argv[1]); p.mkdir(); (p/"data").write_bytes(b"x"*4096); '
                '(p/"environment").write_text(os.environ["DOTNET_ADD_GLOBAL_TOOLS_TO_PATH"]); '
                'time.sleep(.1)')
        warning = io.StringIO()
        with patch.object(g, 'space_status', return_value=self.healthy_space()), \
                patch.dict(os.environ, {'DOTNET_ADD_GLOBAL_TOOLS_TO_PATH': 'true'}), \
                contextlib.redirect_stderr(warning):
            code = g.run_bounded([sys.executable, '-B', '-c', code, str(self.output)], self.output,
                                 1024, scratch=self.root, interval=.01, budget_policy='advisory')
        self.assertEqual(code, 0)
        self.assertEqual((self.output/'data').stat().st_size, 4096)
        self.assertEqual((self.output/'environment').read_text(), 'false')
        receipt = self.receipt()
        self.assertEqual(receipt['Status'], 'finished')
        self.assertEqual(receipt['BudgetBytes'], 1024)
        self.assertTrue(receipt['ForecastExceeded'])
        self.assertGreaterEqual(receipt['ForecastOverrunCount'], 1)
        self.assertGreater(receipt['CurrentForecastBytes'], receipt['FinalBytes'])
        self.assertIn('warning', warning.getvalue())
        self.assertFalse((self.root/'.storage/active.lock').exists())

    def test_advisory_terminal_overrun_is_resampled_and_reestimated(self):
        child = Mock(pid=12345)
        child.poll.return_value = 0
        warning = io.StringIO()
        with patch.object(g, 'tree_bytes', side_effect=[0, 1, 200]), \
                patch.object(g, 'space_status', return_value=self.healthy_space()), \
                patch.object(g.subprocess, 'Popen', return_value=child), \
                contextlib.redirect_stderr(warning):
            self.assertEqual(g.run_bounded(['fake'], self.output, 100, scratch=self.root,
                                          budget_policy='advisory'), 0)
        receipt = self.receipt()
        self.assertEqual(receipt['FinalBytes'], 200)
        self.assertEqual(receipt['SampledPeakBytes'], 200)
        self.assertEqual(receipt['SampleCount'], 2)
        self.assertEqual(receipt['LatestForecastOverrun']['Phase'], 'terminal')
        child.kill.assert_not_called()

    def test_advisory_resume_existing_overrun_keeps_bytes_and_finishes(self):
        self.output.mkdir()
        preserved = self.output/'original'
        preserved.write_bytes(b'x'*4096)
        warning = io.StringIO()
        with patch.object(g, 'space_status', return_value=self.healthy_space()), \
                contextlib.redirect_stderr(warning):
            result = g.run_bounded([sys.executable, '-B', '-c', 'pass'], self.output, 1024,
                                   resume=True, scratch=self.root, interval=.01,
                                   budget_policy='advisory')
        self.assertEqual(result, 0)
        self.assertEqual(preserved.read_bytes(), b'x'*4096)
        receipt = self.receipt()
        self.assertEqual(receipt['PreflightAdditionalBytes'], 1024)
        self.assertEqual(receipt['FirstForecastOverrun']['Phase'], 'resume')
        self.assertEqual(receipt['Status'], 'finished')

    def test_advisory_preflight_includes_practical_headroom(self):
        output_space = dict(Volume=self.output.resolve().anchor, FreeBytes=15*g.GIB+1100,
                            FreeGiB=15, ReserveGiB=15)
        with patch.object(g, 'space_status', return_value=[output_space]), \
                patch.object(g.subprocess, 'Popen') as start:
            with self.assertRaisesRegex(RuntimeError, 'including reserve'):
                g.run_bounded(['unused'], self.output, 1000, scratch=self.root,
                              budget_policy='advisory')
            start.assert_not_called()
        self.assertFalse((self.root/'.storage').exists())

    def test_advisory_reserve_breach_stops_only_owned_process(self):
        owned = Mock(pid=12345)
        owned.poll.return_value = None
        unrelated = Mock(pid=54321)
        low = self.healthy_space()
        low[0].update(FreeBytes=10*g.GIB-1, FreeGiB=10)
        def settle(process):
            self.assertIs(process, owned)
            owned.poll.return_value = 9
        with patch.object(g, 'space_status', side_effect=[self.healthy_space(), low]), \
                patch.object(g.subprocess, 'Popen', return_value=owned), \
                patch.object(g, 'stop_owned', side_effect=settle) as stop:
            with self.assertRaisesRegex(RuntimeError, 'including reserve'):
                g.run_bounded(['fake'], self.output, 100, scratch=self.root,
                              budget_policy='advisory')
        stop.assert_called_once_with(owned)
        unrelated.kill.assert_not_called()
        self.assertEqual(self.receipt()['Status'], 'stopped')
        self.assertFalse((self.root/'.storage/active.lock').exists())

    def test_advisory_single_owner_lock_is_not_stolen(self):
        registry = self.root/'.storage'
        registry.mkdir()
        lock = registry/'active.lock'
        lock.write_text('other owner')
        with patch.object(g, 'space_status', return_value=self.healthy_space()), \
                patch.object(g.subprocess, 'Popen') as start:
            with self.assertRaises(FileExistsError):
                g.run_bounded(['unused'], self.output, 100, scratch=self.root,
                              budget_policy='advisory')
            start.assert_not_called()
        self.assertEqual(lock.read_text(), 'other owner')

    def test_terminal_reserve_breach_cannot_be_reported_as_success(self):
        child = Mock(pid=12345)
        child.poll.return_value = 0
        low = self.healthy_space()
        low[1].update(FreeBytes=15*g.GIB-1, FreeGiB=15)
        with patch.object(g, 'space_status', side_effect=[self.healthy_space(), self.healthy_space(), low]), \
                patch.object(g.subprocess, 'Popen', return_value=child), \
                patch.object(g, 'stop_owned') as stop:
            with self.assertRaisesRegex(RuntimeError, 'including reserve'):
                g.run_bounded(['fake'], self.output, 100, scratch=self.root,
                              budget_policy='advisory')
        self.assertEqual(self.receipt()['Status'], 'stopped')
        stop.assert_called_once_with(child)

    def test_failed_settlement_retains_exclusive_lock(self):
        child = Mock(pid=12345)
        child.poll.return_value = None
        low = self.healthy_space()
        low[1].update(FreeBytes=0, FreeGiB=0)
        with patch.object(g, 'space_status', side_effect=[self.healthy_space(), low]), \
                patch.object(g.subprocess, 'Popen', return_value=child), \
                patch.object(g, 'stop_owned', side_effect=RuntimeError('could not settle')):
            with self.assertRaisesRegex(RuntimeError, 'could not settle'):
                g.run_bounded(['fake'], self.output, 100, scratch=self.root,
                              budget_policy='advisory')
        self.assertTrue((self.root/'.storage/active.lock').exists())
        self.assertEqual(self.receipt()['Status'], 'cleanup-failed')

    def test_tree_and_output_reject_links_and_junctions(self):
        self.output.mkdir()
        outside = self.root/'target'
        outside.mkdir()
        (outside/'data').write_bytes(b'preserve')
        link = self.output/'linked'
        if os.name == 'nt':
            import subprocess
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(outside)],
                           check=True, stdout=subprocess.DEVNULL)
        else:
            link.symlink_to(outside, target_is_directory=True)
        self.addCleanup(lambda: link.rmdir() if link.is_dir() and not link.is_symlink()
                        else link.unlink())
        with self.assertRaisesRegex(RuntimeError, 'Linked output'):
            g.tree_bytes(self.output)
        with self.assertRaisesRegex(RuntimeError, 'Linked output ancestor'):
            g.validate_output(link/'child', self.output)
        self.assertEqual((outside/'data').read_bytes(), b'preserve')

    def test_invalid_policy_or_headroom_never_launches(self):
        for arguments in (dict(budget_policy='unknown'),
                          dict(forecast_headroom_percent=0),
                          dict(forecast_headroom_percent=float('nan'))):
            with self.subTest(arguments=arguments), patch.object(g.subprocess, 'Popen') as start:
                with self.assertRaises(ValueError):
                    g.run_bounded(['unused'], self.output, 100, scratch=self.root, **arguments)
                start.assert_not_called()

    def test_status_uses_unrounded_reserve_bytes(self):
        rows = [dict(Volume='C:/', FreeBytes=10*g.GIB-1, FreeGiB=10, ReserveGiB=10)]
        output = io.StringIO()
        with patch.object(g, 'space_status', return_value=rows), \
                patch.object(sys, 'argv', ['storage_guard.py', 'status']), \
                contextlib.redirect_stdout(output):
            self.assertEqual(g.main(), 0)
        self.assertFalse(json.loads(output.getvalue())['HeavyWorkReady'])


if __name__ == '__main__':
    unittest.main()
