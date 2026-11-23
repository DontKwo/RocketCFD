# Security Policy

## Supported Versions & Official Releases

| Version / Branch | Supported | Notes |
| :--- | :--- | :--- |
| `main` (Latest `vX.Y.Z` Release) | Yes | Actively maintained official release stream |
| Forks, Mirrors, and Older Tags | No | Unverified and unsupported |

Official executables are distributed exclusively from the primary `DontKwo/RocketCFD` repository on GitHub (`main` branch and official [Releases](https://github.com/DontKwo/RocketCFD/releases/latest)).

- **Fork Safety Warning**: Do **not** download or run executables from forked repositories or third-party mirrors unless you have verified the source code yourself and confirmed they contain no malware. Only `DontKwo/RocketCFD` `main` builds are maintained by the author.
- **OS Security Prompts**: Because RocketCFD is published independently without paid commercial code-signing certificates, Windows SmartScreen and macOS Gatekeeper may warn that the download is unrecognized or potentially unsafe. Review the [Desktop Installation Guide](docs/INSTALLATION.md) and bypass OS prompts strictly at your own discretion.

## Engineering & System Safety Disclaimer

RocketCFD automates mesh generation, OpenFOAM solver selection, and local/WSL filesystem case writes. Generated CFD setups are analytical engineering aids and do not replace certified wind-tunnel testing, structural margin reviews, or range-safety approval. RocketCFD is provided "AS IS" under the [MIT License](LICENSE), without warranty of any kind. You run executables and generated OpenFOAM cases entirely at your own risk and discretion.

## Reporting a Vulnerability

If you discover a security issue in `DontKwo/RocketCFD`:

1. **Do not** disclose exploit details or credentials in a public GitHub Issue.
2. Open a [Private Vulnerability Report](https://github.com/DontKwo/RocketCFD/security/advisories/new) on GitHub (or contact `@DontKwo` via GitHub profile).
3. Include reproduction steps, operating system, and any suggested fix.

## Related Documentation

- [Project Overview](README.md)
- [Desktop Installation Guide](docs/INSTALLATION.md)
- [OpenFOAM Installation Guide](docs/OPENFOAM_INSTALLATION.md)
- [User Guide](docs/USER_GUIDE.md)
- [Developer Guide](docs/DEVELOPMENT.md)
- [License](LICENSE)
