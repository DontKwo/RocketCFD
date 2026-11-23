# OpenFOAM Installation Guide

RocketCFD's geometry builder, 1976 Standard Atmosphere calculator, Mach regime selector, and OpenFOAM dictionary exporter work standalone out of the box. Install **OpenFOAM (v2412 recommended)** separately when you want RocketCFD to run live CFD meshes (`blockMesh`, `snappyHexMesh`) and solver sweeps on your machine.

## Platform Installation Instructions

### Windows

The recommended, native-performance OpenFOAM workflow on Windows 10/11 uses **WSL2 (Windows Subsystem for Linux)** with Ubuntu:

1. **Enable WSL2 and install Ubuntu** in an Administrator PowerShell prompt:
   ```powershell
   wsl --install -d Ubuntu-24.04
   ```
   Restart Windows if prompted and complete your initial Ubuntu username and password setup.
2. **Install OpenFOAM inside your Ubuntu WSL terminal** (from openfoam.com APT repository):
   ```bash
   curl -s https://dl.openfoam.com/add-debian-repo.sh | sudo bash
   sudo apt-get update
   sudo apt-get install -y openfoam2412-default
   ```
3. **Verify environment path**: OpenFOAM installs under `/usr/lib/openfoam/openfoam2412`. RocketCFD auto-detects `/usr/lib/openfoam/openfoam*/etc/bashrc` inside WSL2 automatically.

Alternatively, you can use **Docker Desktop for Windows** with the official OpenCFD Windows Docker package when running containerized Linux solvers manually.

### macOS

OpenCFD does not distribute pre-compiled native macOS `.dmg` installers. macOS users have two supported options:

1. **Docker Desktop for Mac** *(Recommended)*: Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and run an official OpenCFD OpenFOAM Linux container against your exported case folder.
2. **Build from Source on a Case-Sensitive Volume**: Install build prerequisites via Homebrew (`brew install open-mpi boost cgal metis scotch fftw vtk`) and follow [OpenFOAM Source Build Instructions](https://develop.openfoam.com/Development/openfoam/-/blob/master/doc/Build.md).

You can still design rocket geometry, compute Mach/Reynolds regimes, validate reference benchmarks, and export ready-to-run OpenFOAM case directories natively inside the macOS desktop app.

### Linux

OpenCFD publishes native Debian and Ubuntu packages for OpenFOAM v2412:

```bash
curl -s https://dl.openfoam.com/add-debian-repo.sh | sudo bash
sudo apt-get update
sudo apt-get install -y openfoam2412-default
```

Add OpenFOAM environment activation to new shell sessions or activate it before CLI runs:

```bash
source /usr/lib/openfoam/openfoam2412/etc/bashrc
```

RocketCFD automatically probes standard `/usr/lib/openfoam/openfoam*/etc/bashrc` and `/opt/openfoam*/etc/bashrc` paths when present.

## Related Documentation

- [Project Overview](../README.md)
- [Desktop Installation Guide](INSTALLATION.md)
- [User Guide](USER_GUIDE.md)
- [Theoretical Background](THEORY.md)
- [Developer Guide](DEVELOPMENT.md)
- [Security Policy](../SECURITY.md)
