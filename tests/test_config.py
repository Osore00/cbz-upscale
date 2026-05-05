from pathlib import Path

import pytest
from pydantic import ValidationError

from cbz_upscale.config import (
    AppConfig,
    DummySettings,
    RealEsrganSettings,
    build_config,
    generate_default_config,
    load_yaml_config,
)


def test_realesrgan_settings_defaults():
    settings = RealEsrganSettings()
    assert settings.exe_path == "realesrgan-ncnn-vulkan"
    assert settings.scale == 4
    assert settings.model == "realesrgan-x4plus-anime"
    assert settings.gpu_id is None
    assert settings.tile_size == 0
    assert settings.threads == "1:2:2"
    assert settings.tta_mode is False
    assert settings.output_format == "png"


def test_dummy_settings_defaults():
    settings = DummySettings()
    assert settings.prefix == "page"
    assert settings.start_number == 1
    assert settings.zero_padding == 3
    assert settings.output_format == "png"


def test_realesrgan_settings_validation():
    # Valid scales
    RealEsrganSettings(scale=2)
    RealEsrganSettings(scale=3)
    RealEsrganSettings(scale=4)

    # Invalid scale
    with pytest.raises(ValidationError):
        RealEsrganSettings(scale=5)  # type: ignore


def test_app_config_defaults(tmp_path: Path):
    input_path = tmp_path / "test.cbz"
    config = AppConfig(input=input_path)

    assert config.input == input_path
    assert config.output is None
    assert config.upscaler == "realesrgan"
    assert config.suffix == "_upscaled"
    assert config.keep_temp is False
    assert config.verbose is False


def test_get_upscaler_settings(tmp_path: Path):
    input_path = tmp_path / "test.cbz"

    # Default is realesrgan
    config = AppConfig(input=input_path)
    settings = config.get_upscaler_settings()
    assert isinstance(settings, RealEsrganSettings)

    # Change to dummy
    config = AppConfig(input=input_path, upscaler="dummy")
    settings = config.get_upscaler_settings()
    assert isinstance(settings, DummySettings)

    # Invalid upscaler
    config = AppConfig(input=input_path, upscaler="unknown")
    with pytest.raises(ValueError, match="Unknown upscaler"):
        config.get_upscaler_settings()


def test_load_yaml_config(tmp_path: Path):
    yaml_content = """
    upscaler: dummy
    suffix: _test
    dummy:
      prefix: chapter
      start_number: 10
    """
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(yaml_content)

    config_dict = load_yaml_config(yaml_path)
    assert config_dict["upscaler"] == "dummy"
    assert config_dict["suffix"] == "_test"
    assert config_dict["dummy"]["prefix"] == "chapter"
    assert config_dict["dummy"]["start_number"] == 10


def test_build_config_merging(tmp_path: Path):
    # Create YAML config
    yaml_content = """
    upscaler: dummy
    suffix: _yaml
    dummy:
      prefix: chapter
      start_number: 10
    """
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(yaml_content)

    input_path = tmp_path / "test.cbz"

    # CLI overrides YAML
    dummy_overrides = {"start_number": 5, "zero_padding": 4}

    config = build_config(
        yaml_path=yaml_path,
        input=input_path,
        upscaler="realesrgan",  # CLI override
        dummy=dummy_overrides,  # CLI overrides
    )

    assert config.input == input_path
    assert config.upscaler == "realesrgan"  # overridden by CLI
    assert config.suffix == "_yaml"  # from YAML

    # Check dummy settings were merged
    assert config.dummy.prefix == "chapter"  # from YAML
    assert config.dummy.start_number == 5  # overridden by CLI
    assert config.dummy.zero_padding == 4  # overridden by CLI


def test_generate_default_config():
    yaml_str = generate_default_config()

    # Check that it contains comments and default values
    assert "realesrgan-ncnn-vulkan" in yaml_str
    assert "realesrgan-x4plus-anime" in yaml_str
    assert "dummy:" in yaml_str
    assert 'prefix: "page"' in yaml_str
