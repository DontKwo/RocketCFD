# Desktop Installation Guide

Download the official standalone desktop executable from [RocketCFD Latest Releases](https://github.com/DontKwo/RocketCFD/releases/latest). Only download packages from the primary `DontKwo/RocketCFD` repository.

> [!WARNING]
> Because RocketCFD releases are independently compiled without commercial code-signing certificates, operating systems may warn that the binary is unrecognized or unsafe. Verify the release comes strictly from `DontKwo/RocketCFD` `main` and bypass prompts at your own discretion.

## Platform Installation Instructions

### Windows

1. Download **`RocketCFD-Windows.exe`** from the [Latest Releases](https://github.com/DontKwo/RocketCFD/releases/latest) page.
2. Double-click the executable to launch RocketCFD Studio in your default browser.
3. If **Windows SmartScreen** displays *"Windows protected your PC"*:
   - Click **More info**, verify the file originated from the official GitHub release, and click **Run anyway** at your own discretion.
4. *(Optional)* To run live OpenFOAM CFD solves from Windows, follow the [OpenFOAM Windows (WSL2) Guide](OPENFOAM_INSTALLATION.md#windows).

### macOS

1. Download **`RocketCFD-macOS.zip`** from the [Latest Releases](https://github.com/DontKwo/RocketCFD/releases/latest) page.
2. Double-click `RocketCFD-macOS.zip` in Finder to extract **`RocketCFD.app`**, then move it to your Applications folder.
3. On first launch, if **macOS Gatekeeper** warns that the developer cannot be verified:
   - Control-click (right-click) **`RocketCFD.app`**, click **Open**, or go to **System Settings -> Privacy & Security** and click **Open Anyway** at your own discretion.
4. *(Optional)* To solve exported OpenFOAM cases on macOS, review the [OpenFOAM macOS Guide](OPENFOAM_INSTALLATION.md#macos).

### Linux

1. Download **`RocketCFD-Linux.tar.gz`** from the [Latest Releases](https://github.com/DontKwo/RocketCFD/releases/latest) page.
2. Extract the executable and mark it runnable:
   ```bash
   tar -xzf RocketCFD-Linux.tar.gz
   chmod +x RocketCFD-Linux
   ./RocketCFD-Linux
   ```
3. *(Optional)* Install native OpenFOAM packages via the [OpenFOAM Linux Guide](OPENFOAM_INSTALLATION.md#linux) to execute solves directly.

## Related Documentation

- [Project Overview](../README.md)
- [OpenFOAM Installation Guide](OPENFOAM_INSTALLATION.md)
- [User Guide](USER_GUIDE.md)
- [Developer Guide](DEVELOPMENT.md)
- [Security Policy](../SECURITY.md)
