from pathlib import Path

from cbz_upscale.config import DummySettings
from cbz_upscale.upscalers import UpscalerRegistry
from cbz_upscale.upscalers.dummy import DummyUpscaler


def test_dummy_registration():
    backends = UpscalerRegistry.get_all()
    assert "dummy" in backends
    assert backends["dummy"] == DummyUpscaler


def test_dummy_validate_environment():
    upscaler = DummyUpscaler(DummySettings())
    # Should not raise any exceptions
    upscaler.validate_environment()


def test_dummy_upscale_directory(tmp_path: Path):
    # Setup input
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "01.png").touch()
    (input_dir / "02.jpg").touch()
    (input_dir / "sub").mkdir()
    (input_dir / "sub" / "03.webp").touch()
    (input_dir / "not_an_image.txt").touch()

    output_dir = tmp_path / "output"

    settings = DummySettings(
        prefix="test",
        start_number=10,
        zero_padding=4,
        output_format="png",
    )
    upscaler = DummyUpscaler(settings)

    # Track callbacks
    callbacks = []

    def progress(current: int, total: int):
        callbacks.append((current, total))

    # Run
    upscaler.upscale_directory(input_dir, output_dir, progress_callback=progress)

    # Verify outputs
    out_files = sorted([f.name for f in output_dir.iterdir() if f.is_file()])

    assert len(out_files) == 3
    assert out_files[0] == "test_0010.png"
    assert out_files[1] == "test_0011.png"
    assert out_files[2] == "test_0012.png"

    # Verify non-image was ignored
    assert not (output_dir / "test_0013.png").exists()

    # Verify callbacks
    assert len(callbacks) == 3
    assert callbacks[0] == (1, 3)
    assert callbacks[1] == (2, 3)
    assert callbacks[2] == (3, 3)
