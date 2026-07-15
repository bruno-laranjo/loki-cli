# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build spec for loki-cli.
#
# Build a single-file executable (per platform):
#
#   pip install -e ".[build]"
#   pyinstaller --clean --noconfirm loki-cli.spec
#
# Output: dist/loki-cli (Linux/macOS) or dist\loki-cli.exe (Windows).

from pathlib import Path

project_root = Path.cwd()
entry_script = str(project_root / "src" / "loki_cli" / "__main__.py")
src_path = str(project_root / "src")

a = Analysis(
    [entry_script],
    pathex=[src_path],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="loki-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX often flagged by AV on Windows; keep off
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,       # This is a CLI tool
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
