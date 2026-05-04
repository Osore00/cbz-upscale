# CBZ Upscale

CLI tool for upscaling CBZ comic book archives using AI upscalers like Real-ESRGAN.

## Features
- **Modular Backend:** Supports multiple upscaler plugins (Real-ESRGAN, dummy for testing).
- **Clean Architecture:** Simple pipeline for extracting, processing, and repacking.
- **Smart Config:** Centralized YAML configuration with Typer CLI overrides.
- **Rich Output:** Beautiful CLI progress bars and colored logging.

## Installation
```bash
pip install -e .
```

## Usage
Run `cbz-upscale --help` to see available options.
