# Coolie

Coolie is an AI-assisted business workroom for research, planning, finance, and controlled operations. This project is under active development.

## Download

Installers for Windows, macOS, and Linux are available from the [latest release](https://github.com/Newman10p/coolie/releases/latest):

- [Windows x64](https://github.com/Newman10p/coolie/releases/latest/download/Coolie-Windows-Setup.exe)
- [macOS Intel](https://github.com/Newman10p/coolie/releases/latest/download/Coolie-macOS-Intel.dmg)
- [macOS Apple silicon](https://github.com/Newman10p/coolie/releases/latest/download/Coolie-macOS-Apple-Silicon.dmg)
- [Linux x86_64](https://github.com/Newman10p/coolie/releases/latest/download/Coolie-Linux-x86_64.sh)

The app includes guided owner setup and local settings. In the signed-in UI, choose **Local settings** to save or replace the AI provider API key. Keys are stored in the local user profile and are not returned to the browser. A key alone does not enable AI: a compatible provider service must also be configured.

Use **Check for updates** in the app to find the latest desktop build and download the installer for your platform. Development builds are refreshed from `main`; routine updates do not require a new version tag. Close Coolie before installing an update.

## Development

Requirements: Python 3.11+, Node.js 22+, and npm.

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
npm ci
npm run build
```

To run the local preview:

```bash
python -m ui.demo_server
npm run dev
```

## Project

- [Issues](https://github.com/Newman10p/coolie/issues)
- [Releases](https://github.com/Newman10p/coolie/releases)

Do not commit credentials or private configuration files.
