# Build on Windows: python -m PyInstaller OctoKit.spec
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('scripts/*.ps1', 'scripts')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='OctoKit',
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='OctoKit')
