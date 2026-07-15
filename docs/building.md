# Building standalone binaries

`loki-cli` ships a [PyInstaller](https://pyinstaller.org/) spec that produces
a single-file executable per platform. PyInstaller cannot cross-compile, so a
Linux binary must be built on Linux and a Windows `.exe` on Windows.

## Local build

```bash
make install         # brings in the [build] extras
make build-binary    # runs pyinstaller --clean --noconfirm loki-cli.spec
```

Output:

- Linux / macOS: `dist/loki-cli` (~11 MB, no Python needed at runtime)
- Windows:       `dist\loki-cli.exe`

Smoke test:

```bash
./dist/loki-cli --version
./dist/loki-cli whoami
```

## Cross-platform builds via CI

The workflow at `.github/workflows/build.yml` builds the binary on both
`ubuntu-latest` and `windows-latest` and uploads each as a workflow artifact.

Triggers:

- **Manual dispatch** — via the Actions tab.
- **Tag push matching `v*`** — publishes the binaries as GitHub Release
  assets in addition to the artifact uploads:
    - `loki-cli-linux-x86_64`
    - `loki-cli-windows-x86_64.exe`

Both artifacts are smoke-tested (`--version`, `--help`) as part of the job.

## Notes

- The spec disables UPX because compressed binaries are frequently
  false-positive-flagged by Windows antivirus scanners.
- The binary bundles a Python interpreter and all deps — no `python`
  install is required on the target machine. It reads the same
  `~/.config/loki-cli/config.json` file (or
  `%USERPROFILE%\.config\loki-cli\config.json` on Windows).
