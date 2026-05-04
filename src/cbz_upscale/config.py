"""Configuration models and loader for CBZ Upscale."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings

class UpscalerSettings(BaseModel):
    """Base class for upscaler backend settings."""
    output_format: str = "png"

class RealEsrganSettings(UpscalerSettings):
    """Configuration specific to the Real-ESRGAN backend."""
    exe_path: str = "realesrgan-ncnn-vulkan"
    scale: Literal[2, 3, 4] = 4
    model: str = "realesrgan-x4plus-anime"
    gpu_id: list[int] | None = None
    tile_size: list[int] | int = 0
    threads: str = "1:2:2"
    tta_mode: bool = False

class DummySettings(UpscalerSettings):
    """Configuration specific to the Dummy test backend."""
    prefix: str = "page"
    start_number: int = 1
    zero_padding: int = 3

class AppConfig(BaseSettings):
    """Main application configuration.
    
    Can be loaded from YAML, environment variables, or CLI overrides.
    CLI overrides take precedence.
    """
    input: Path | None = None  # Optional because it's usually provided via CLI args directly
    output: Path | None = None
    upscaler: str = "realesrgan"
    suffix: str = "_upscaled"
    keep_temp: bool = False
    verbose: bool = False
    
    # Backend-specific nested settings
    realesrgan: RealEsrganSettings = RealEsrganSettings()
    dummy: DummySettings = DummySettings()

    def get_upscaler_settings(self) -> UpscalerSettings:
        """Return the specific settings object for the currently active upscaler."""
        return getattr(self, self.upscaler)

def load_yaml_config(path: Path) -> dict:
    """Load configuration dictionary from a YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        
    return data if data is not None else {}

def build_config(yaml_path: Path | None = None, **cli_kwargs) -> AppConfig:
    """Build the final configuration by merging YAML and CLI arguments.
    
    Priority: CLI arguments > YAML config > Defaults.
    """
    config_dict = {}
    
    # 1. Load from YAML if provided
    if yaml_path:
        config_dict.update(load_yaml_config(yaml_path))
        
    # 2. Override with CLI kwargs (only non-None values)
    cli_overrides = {k: v for k, v in cli_kwargs.items() if v is not None}
    
    # Handle nested backend settings if provided via CLI
    # Currently CLI arguments are flat, we will map them in the CLI layer
    # or rely on the pipeline to build nested dicts if needed.
    # For now, we update the root level.
    config_dict.update(cli_overrides)
    
    return AppConfig(**config_dict)

def generate_default_config() -> str:
    """Generate a default config.yaml string with comments."""
    # We could serialize AppConfig().model_dump() but a hand-crafted string
    # provides better comments and structure for the user.
    return """# CBZ Upscale Configuration
# This file defines the default settings for the application.
# CLI arguments will override these values.

upscaler: realesrgan
suffix: "_upscaled"
keep_temp: false
verbose: false

# Settings for Real-ESRGAN backend
realesrgan:
  exe_path: "realesrgan-ncnn-vulkan"
  scale: 4
  model: "realesrgan-x4plus-anime"
  # gpu_id: [0, 1]          # Uncomment for multi-GPU
  tile_size: 0              # 0 means auto
  threads: "1:2:2"          # "load:proc:save", multi-GPU format: "1:2,2:2"
  tta_mode: false
  output_format: "png"

# Settings for Dummy test backend
dummy:
  prefix: "page"
  start_number: 1
  zero_padding: 3
  output_format: "png"
"""
