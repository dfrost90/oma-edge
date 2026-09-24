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
    id: barWindow
    exclusionMode: root.barHidden ? ExclusionMode.Ignore : ExclusionMode.Auto
    margins {
      left: root.barHidden && root.position === "left" ? -root.barSize : 0
      right: root.barHidden && root.position === "right" ? -root.barSize : 0
    }
  }
}
'''

class InstallTests(unittest.TestCase):
    def test_legacy_adapter_removal_is_exact_and_idempotent(self):
        legacy = (Path(__file__).parent/'fixtures/legacy_bar.qml').read_text()
        self.assertEqual(installer.remove_bar_adapter(legacy), BAR)
        self.assertEqual(installer.remove_bar_adapter(BAR), BAR)

    def test_setup_accepts_standard_or_unrelated_custom_bar(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)
            (config/'hypr').mkdir()
            (config/'omarchy').mkdir()
            (config/'hypr/hyprland.lua').write_text('-- config')
            for bar in ('omarchy.bar', 'unrelated.custom-bar'):
                (config/'omarchy/shell.json').write_text('{"bar":{"id":"'+bar+'"}}')
                with patch.object(installer, 'CFG', config), patch.object(installer.shutil, 'which', return_value='/bin/tool'):
                    installer.preflight()
                self.assertFalse((config/'omarchy/plugins').exists())

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
