"""Check installed package payload and runtime without accessing hardware."""
import importlib
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

archive = pathlib.Path(sys.argv[1])
files = set(subprocess.check_output(['bsdtar', '-tf', str(archive)], text=True).splitlines())
required = [
    'usr/lib/udev/rules.d/70-trcc-lcd.rules',
    'usr/lib/udev/rules.d/70-trcc-rgb.rules',
    'usr/lib/sysusers.d/trcc.conf',
    'usr/lib/modprobe.d/trcc-lcd.conf',
    'usr/lib/modules-load.d/trcc-sg.conf',
    'usr/lib/modules-load.d/trcc-rapl.conf',
    'usr/lib/systemd/user/trccd.service',
    'usr/share/applications/trcc-linux.desktop',
]
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
subprocess.run(['trcc', '--help'], check=True)
subprocess.run(['trcc', 'api', '--help'], check=True)
subprocess.run(['systemd-analyze', '--user', 'verify',
                '/usr/lib/systemd/user/trccd.service'], check=True)
print('Package payload, policy helpers, runtime imports, CLI/API and user unit verified.')
