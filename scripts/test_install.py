"""Exercise installer downloads and daemon synchronization without touching user state."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
VERSION = '0.159.1002'


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'tools'
        self.bin.mkdir()
        self.installed = self.root / 'install'
        self.state = self.root / 'daemon'
        self.calls = self.root / 'calls'
        self.env = dict(os.environ, PATH=f'{self.bin}:/usr/bin:/bin:/usr/sbin:/sbin',
                        CODEX_INSTALL_DIR=str(self.installed), FIXTURE=str(self.root),
                        DAEMON_STATE=str(self.state), CALLS=str(self.calls))
        self.executable(self.bin / 'rg', '#!/bin/sh\nexit 0\n')
        self.executable(self.bin / 'uname', '#!/bin/sh\ncase "$1" in -s) echo Darwin;; -m) echo arm64;; esac\n')
        self.executable(self.bin / 'curl', '''#!/bin/bash
printf '%s\\n' "$*" >> "$FIXTURE/downloads"
if [[ "$*" == *url_effective* ]]; then
  echo https://github.com/celados/codex-build/releases/tag/rust-v0.159.1002
else
  src="${2##*/}"
  cp "$FIXTURE/$src" "$4"
fi
''')
        self.executable(self.root / 'codex-aarch64-apple-darwin', '''#!/bin/bash
case "$*" in
  --version) echo 'codex-cli 0.159.1002';;
  'app-server daemon update --help') echo --from-cli;;
  'app-server daemon version')
    [[ -f "$DAEMON_STATE" ]] || exit 1
    version="$(cat "$DAEMON_STATE")"
    printf '{"cliVersion":"0.159.1002","appServerVersion":"%s","managedCodexVersion":"%s"}\\n' "$version" "$version";;
  'app-server daemon update --from-cli --yes')
    echo update >> "$CALLS"
    [[ "${FAIL_UPDATE:-}" != 1 ]] || exit 1
    if [[ "${STALE_UPDATE:-}" != 1 ]]; then echo 0.159.1002 > "$DAEMON_STATE"; fi;;
  *) exit 2;;
esac
''')
        self.executable(self.root / 'codex-code-mode-host-aarch64-apple-darwin', '#!/bin/sh\nexit 0\n')
        asset = self.root / 'codex-aarch64-apple-darwin.tar.gz'
        with tarfile.open(asset, 'w:gz') as archive:
            for name in ['codex-aarch64-apple-darwin', 'codex-code-mode-host-aarch64-apple-darwin']:
                archive.add(self.root / name, arcname=name)
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        (self.root / (asset.name + '.sha256')).write_text(f'{digest}  {asset.name}\n')

    def executable(self, path, text):
        path.write_text(text)
        path.chmod(0o755)

    def run_install(self, **extra):
        return subprocess.run(['bash', str(ROOT / 'install.sh')], env=dict(self.env, **extra),
                              text=True, capture_output=True)

    def test_first_install_builds_complete_package_without_starting_daemon(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        package = self.installed / '.codex-build/releases' / VERSION
        self.assertEqual(json.loads((package / 'codex-package.json').read_text())['version'], VERSION)
        for name in ['bin/codex', 'bin/codex-code-mode-host', 'codex-path/rg']:
            self.assertTrue(os.access(package / name, os.X_OK))
        self.assertEqual((self.installed / 'codex').resolve(), (package / 'bin/codex').resolve())
        self.assertFalse(self.calls.exists())

    def test_running_daemon_updates_and_repeated_install_repairs_without_download(self):
        self.state.write_text('0.159.1000')
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.state.read_text().strip(), VERSION)
        downloads = (self.root / 'downloads').read_text().count(' -o ')
        self.state.write_text('0.159.1000')
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.state.read_text().strip(), VERSION)
        self.assertEqual((self.root / 'downloads').read_text().count(' -o '), downloads + 1)
        self.assertEqual(self.calls.read_text().splitlines(), ['update', 'update'])

    def test_daemon_update_failure_is_not_install_success_and_can_retry(self):
        self.state.write_text('0.159.1000')
        result = self.run_install(FAIL_UPDATE='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('daemon update failed', result.stderr)
        self.assertNotIn('Installed codex', result.stdout)
        self.assertEqual(self.run_install().returncode, 0)

    def test_stale_daemon_version_is_rejected(self):
        self.state.write_text('0.159.1000')
        result = self.run_install(STALE_UPDATE='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Daemon version verification failed', result.stderr)

    def test_checksum_failure_keeps_existing_cli(self):
        self.installed.mkdir()
        previous = self.installed / 'codex'
        self.executable(previous, '#!/bin/sh\necho old\n')
        (self.root / 'codex-aarch64-apple-darwin.tar.gz.sha256').write_text(
            '0' * 64 + '  codex-aarch64-apple-darwin.tar.gz\n')
        result = self.run_install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('echo old', previous.read_text())
        self.assertFalse(self.calls.exists())


if __name__ == '__main__':
    unittest.main()
