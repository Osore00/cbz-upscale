from pathlib import Path

from cbz_upscale.config import AppConfig
from cbz_upscale.pipeline import UpscalePipeline


def test_resolve_output_path(tmp_path: Path):
    cbz_path = tmp_path / "comic.cbz"

    # Default (no output defined) -> next to input with suffix
    config = AppConfig(input=cbz_path, suffix="_test")
    pipeline = UpscalePipeline(config)
    assert pipeline._resolve_output_path(cbz_path) == tmp_path / "comic_test.cbz"

    # Specific output file
    out_file = tmp_path / "out_folder" / "custom.cbz"
    config = AppConfig(input=cbz_path, output=out_file)
    pipeline = UpscalePipeline(config)
    assert pipeline._resolve_output_path(cbz_path) == out_file

    # Specific output directory
    out_dir = tmp_path / "out_folder"
    out_dir.mkdir()
    config = AppConfig(input=cbz_path, output=out_dir, suffix="_test")
    pipeline = UpscalePipeline(config)
    assert pipeline._resolve_output_path(cbz_path) == out_dir / "comic_test.cbz"


def test_process_file_with_dummy(sample_cbz: Path, tmp_path: Path):
    # End-to-end test of the pipeline using the Dummy upscaler
    out_cbz = tmp_path / "output.cbz"

    config = AppConfig(
        input=sample_cbz,
        output=out_cbz,
        upscaler="dummy",
    )

    pipeline = UpscalePipeline(config)
    result_path = pipeline.process_file(sample_cbz)

    assert result_path == out_cbz
    assert out_cbz.exists()

    # Temporary directory should be cleaned up
    # We can't easily check the exact temp dir, but we can check there are no
    # "cbz_upscale_*" dirs left in the parent
    temp_dirs = list(tmp_path.glob("cbz_upscale_*"))
    assert len(temp_dirs) == 0


def test_process_file_keep_temp(sample_cbz: Path, tmp_path: Path):
    config = AppConfig(
        input=sample_cbz,
        upscaler="dummy",
        keep_temp=True,
    )

    pipeline = UpscalePipeline(config)
    pipeline.process_file(sample_cbz)

    # Temporary directory SHOULD exist
    temp_dirs = list(sample_cbz.parent.glob("cbz_upscale_*"))
    assert len(temp_dirs) == 1
    assert temp_dirs[0].is_dir()


def test_process_batch_file(sample_cbz: Path, tmp_path: Path):
    config = AppConfig(input=sample_cbz, upscaler="dummy")
    pipeline = UpscalePipeline(config)

    results = pipeline.process_batch(sample_cbz)

    assert len(results) == 1
    assert results[0].name == f"{sample_cbz.stem}_upscaled.cbz"


def test_process_batch_directory(sample_cbz: Path, tmp_path: Path):
    import shutil

    # Create a directory with two cbz files
    batch_dir = tmp_path / "batch"
    batch_dir.mkdir()

    cbz1 = batch_dir / "comic1.cbz"
    cbz2 = batch_dir / "comic2.cbz"

    shutil.copy(sample_cbz, cbz1)
    shutil.copy(sample_cbz, cbz2)

    # Also add a non-cbz file to ensure it's ignored
    (batch_dir / "ignore.txt").write_text("ignore me")

    config = AppConfig(input=batch_dir, upscaler="dummy")
    pipeline = UpscalePipeline(config)

    results = pipeline.process_batch(batch_dir)

    assert len(results) == 2
    assert results[0].name == "comic1_upscaled.cbz"
    assert results[1].name == "comic2_upscaled.cbz"

    assert (batch_dir / "comic1_upscaled.cbz").exists()
    assert (batch_dir / "comic2_upscaled.cbz").exists()
