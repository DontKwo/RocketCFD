# Desktop Installation Guide

Download the official standalone desktop executable from [RocketCFD Latest Releases](https://github.com/DontKwo/RocketCFD/releases/latest).

## Platform Installation Instructions

### Windows

1. Download **`RocketCFD-Windows.exe`** from [Latest Releases](https://github.com/DontKwo/RocketCFD/releases/latest).
2. Double-click the executable to launch RocketCFD Studio in its standalone app window.
3. If **Microsoft Defender SmartScreen** displays *"Windows protected your PC"*:
   - Click **More info**, confirm the release came from `DontKwo/RocketCFD`, and click **Run anyway** at your own discretion.
4. Alternative unblock method: Right-click `RocketCFD-Windows.exe` -> **Properties** -> check **Unblock** under Security -> click **Apply** and **OK** -> launch normally.
5. *(Optional)* To run live OpenFOAM CFD solves from Windows, follow the [OpenFOAM Windows (WSL2) Guide](OPENFOAM_INSTALLATION.md#windows).

### macOS

1. Download **`RocketCFD-macOS.zip`** from [Latest Releases](https://github.com/DontKwo/RocketCFD/releases/latest).
2. Double-click `RocketCFD-macOS.zip` in Finder to extract **`RocketCFD.app`**, then move it into **Applications**.
3. On macOS Sonoma and Sequoia, approve independently distributed apps in **System Settings**:
   - Double-click **`RocketCFD.app`** once so macOS registers the blocked prompt, then click **OK** (or **Done**).
   - Open **System Settings** -> **Privacy & Security** -> scroll to **Security** -> click **Open Anyway** and confirm with your password or Touch ID.
4. Developer Terminal Alternative: run `xattr -cr /Applications/RocketCFD.app` in Terminal, then open **`RocketCFD.app`** normally.
5. *(Optional)* To solve exported OpenFOAM cases on macOS, review the [OpenFOAM macOS Guide](OPENFOAM_INSTALLATION.md#macos).

### Linux

1. Download **`RocketCFD-Linux.tar.gz`** from [Latest Releases](https://github.com/DontKwo/RocketCFD/releases/latest).
2. Extract the archive and mark executable (`tar -xzf RocketCFD-Linux.tar.gz && chmod +x RocketCFD-Linux`), then run `./RocketCFD-Linux`.
3. *(Optional)* Install native OpenFOAM packages via the [OpenFOAM Linux Guide](OPENFOAM_INSTALLATION.md#linux) to execute solves directly.

## Safety & Authenticity Warning

- **Official `main` Releases Only**: Download `RocketCFD` exclusively from [DontKwo/RocketCFD Releases](https://github.com/DontKwo/RocketCFD/releases/latest) (`main` branch).
- **Fork Warning**: Never download builds from forked repositories unless you have verified the source code yourself and know they do not contain malware. Only official `main` releases are maintained by the author, and I make no promises.
- **Bypassing Security Prompts & AS-IS Warranty**: Because independently published binaries do not carry paid commercial signing certificates, Windows and macOS will warn that the app is unrecognized or potentially unsafe. Bypassing warnings is strictly at your own discretion, and `RocketCFD` is provided "AS IS" under the [MIT License](../LICENSE) with zero liability.

## Related Documentation

- [Project Overview](../README.md)
- [OpenFOAM Installation Guide](OPENFOAM_INSTALLATION.md)
- [User Guide](USER_GUIDE.md)
- [Developer Guide](DEVELOPMENT.md)
- [Security Policy](../SECURITY.md)
- [MIT License](../LICENSE)
