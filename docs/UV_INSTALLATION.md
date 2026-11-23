# uv Installation Guide

Contributors and source builders use [uv](https://docs.astral.sh/uv/) to manage RocketCFD's Python 3.13 virtual environment, scientific libraries, and standalone packaging tools. Standalone release binaries do **not** require `uv`.

## Platform Installation Instructions

### Windows

Open PowerShell and run:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen your terminal, then verify with `uv --version`.

### macOS

Open Terminal and install using the standalone script or Homebrew:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or with Homebrew:

```bash
brew install uv
```

Verify installation with `uv --version`.

### Linux

Open a shell and install using `curl` (or `wget`):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart your shell session so `uv` is on your `PATH`, then verify with `uv --version`.

## Related Documentation

- [Project Overview](../README.md)
- [Developer Guide](DEVELOPMENT.md)
- [Desktop Installation Guide](INSTALLATION.md)
- [OpenFOAM Installation Guide](OPENFOAM_INSTALLATION.md)
