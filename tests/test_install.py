import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('installer', Path(__file__).parents[1] / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

BAR = '''Item {
  id: root
  component BarPanel: PanelWindow {
    margins {
      left: root.barHidden && root.position === "left" ? -root.barSize : 0
      right: root.barHidden && root.position === "right" ? -root.barSize : 0
    }
  }
}
'''

class InstallTests(unittest.TestCase):
    def test_adapter_is_idempotent_and_exactly_reversible(self):
        adapted = installer.render_bar_adapter(BAR)
        self.assertIn('root.edgeStripMargin', adapted)
        self.assertEqual(installer.render_bar_adapter(adapted), adapted)
        self.assertEqual(installer.remove_bar_adapter(adapted), BAR)
        self.assertEqual(installer.remove_bar_adapter(BAR), BAR)

    def test_incompatible_bar_is_rejected(self):
        with self.assertRaises(SystemExit):
            installer.render_bar_adapter(BAR.replace('      left:', '      horizontal:'))

    def test_conflicting_installation_is_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)
            target = config / 'omarchy/plugins' / installer.ID
            target.mkdir(parents=True)
            sentinel = target / 'keep.txt'
            sentinel.write_text('existing installation')
            with patch.object(installer, 'CFG', config), patch.object(installer.shutil, 'which', return_value='/bin/tool'):
                with self.assertRaisesRegex(SystemExit, 'refusing to overwrite'):
                    installer.preflight()
            self.assertEqual(sentinel.read_text(), 'existing installation')
            self.assertEqual(list(target.iterdir()), [sentinel])

    def test_failed_setup_restores_changed_files(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)
            file = config/'hyprland.lua'
            file.write_text('original')
            def failing_setup():
                installer.write(file, 'changed')
                raise RuntimeError('simulated failure')
            with patch.multiple(installer, CFG=config, BACKUP=config/'backups', ORIGINALS={}), \
                    patch.object(installer, 'main', side_effect=failing_setup), patch.object(installer, 'run'):
                with self.assertRaisesRegex(RuntimeError, 'simulated failure'):
                    installer.install_safely()
            self.assertEqual(file.read_text(), 'original')
