"""Check installed package payload and runtime without accessing hardware."""
import grp
import importlib
import os
import pathlib
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

archive = pathlib.Path(sys.argv[1])
files = set(subprocess.check_output(['bsdtar', '-tf', str(archive)], text=True).splitlines())
required = [
    'usr/lib/udev/rules.d/70-trcc-lcd.rules',
    'usr/lib/sysusers.d/trcc.conf',
    'usr/lib/modprobe.d/trcc-lcd.conf',
    'usr/lib/modules-load.d/trcc-sg.conf',
    'usr/lib/modules-load.d/trcc-rapl.conf',
    'usr/lib/systemd/user/trccd.service',
    'usr/share/applications/trcc-linux.desktop',
]
pkginfo = subprocess.check_output(['bsdtar', '-xOf', str(archive), '.PKGINFO'], text=True)
is_git = 'pkgname = thermalright-trcc-git\n' in pkginfo
rgb_rule = 'usr/lib/udev/rules.d/70-trcc-rgb.rules'
if is_git:
    assert rgb_rule not in files
    assert 'usr/lib/udev/rules.d/70-trcc-module-rgb.rules' not in files
    required.extend(['usr/bin/trcc-module-devices', 'usr/bin/trcc-module-devices-off'])
else:
    required.append(rgb_rule)
for name in required:
    assert name in files, name
assert 'usr/lib/udev/rules.d/99-trcc-lcd.rules' not in files
assert not any('/site-packages/uvicorn/' in name for name in files)
policy = ET.parse('/usr/share/polkit-1/actions/com.github.lexonight1.trcc.policy')
for annotation in policy.findall('.//annotate'):
    if annotation.attrib.get('key') == 'org.freedesktop.policykit.exec.path':
        target = pathlib.Path(annotation.text)
        if target.name.startswith('trcc-'):
            assert target.is_file() and target.stat().st_mode & 0o111, target
for module in ('trcc', 'PySide6', 'numpy', 'psutil', 'usb', 'pyudev', 'click',
               'typer', 'fastapi', 'uvicorn', 'websockets', 'cryptography',
               'python_multipart', 'prompt_toolkit', 'certifi'):
    importlib.import_module(module)
from trcc.ui.api import build_app
assert build_app(serve=False).openapi()['paths']
assert grp.getgrnam('trcc').gr_name == 'trcc'
udev_rules = ['/usr/lib/udev/rules.d/70-trcc-lcd.rules']
if not is_git:
    udev_rules.append('/usr/lib/udev/rules.d/70-trcc-rgb.rules')
subprocess.run(['udevadm', 'verify', *udev_rules], check=True)
subprocess.run(['trcc', '--help'], check=True)
subprocess.run(['trcc', 'api', '--help'], check=True)
with tempfile.TemporaryDirectory(prefix='trcc-unit-verify-') as runtime:
    subprocess.run(['systemd-analyze', '--user', 'verify',
                    '/usr/lib/systemd/user/trccd.service'], check=True,
                   env={**os.environ, 'XDG_RUNTIME_DIR': runtime})
print('Package payload, policy helpers, runtime imports, CLI/API and user unit verified.')
