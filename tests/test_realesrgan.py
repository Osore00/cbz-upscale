from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cbz_upscale.config import RealEsrganSettings
from cbz_upscale.upscalers import UpscalerRegistry
from cbz_upscale.upscalers.realesrgan import RealEsrganError, RealEsrganUpscaler


def test_realesrgan_registration():
    backends = UpscalerRegistry.get_all()
    assert "realesrgan" in backends
    assert backends["realesrgan"] == RealEsrganUpscaler


@patch("subprocess.run")
def test_validate_environment_success(mock_run):
    # Mock successful run
    mock_run.return_value = MagicMock(returncode=0)

    upscaler = RealEsrganUpscaler(RealEsrganSettings(exe_path="my-realesrgan"))
    upscaler.validate_environment()

    mock_run.assert_called_once()
    assert mock_run.call_args[0][0] == ["my-realesrgan", "-h"]


@patch("subprocess.run")
def test_validate_environment_not_found(mock_run):
    mock_run.side_effect = FileNotFoundError()

    upscaler = RealEsrganUpscaler(RealEsrganSettings())

    with pytest.raises(RealEsrganError, match="Executable not found"):
        upscaler.validate_environment()


def test_build_command(tmp_path: Path):
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"

    # Basic settings
    s1 = RealEsrganSettings(
        exe_path="realesrgan",
        scale=4,
        model="anime",
        output_format="jpg",
    )
    cmd1 = RealEsrganUpscaler(s1)._build_command(in_dir, out_dir)
    assert cmd1 == [
        "realesrgan",
        "-i",
        str(in_dir),
        "-o",
        str(out_dir),
        "-s",
        "4",
        "-n",
        "anime",
        "-f",
        "jpg",
        "-j",
        "1:2:2",
    ]

    # Advanced settings (Multi-GPU, TTA, etc.)
    s2 = RealEsrganSettings(
        exe_path="realesrgan",
        gpu_id=[0, 1],
        tile_size=[200, 400],
        threads="1:2,2:2",
        tta_mode=True,
    )
    cmd2 = RealEsrganUpscaler(s2)._build_command(in_dir, out_dir)

    assert "-g" in cmd2
    assert cmd2[cmd2.index("-g") + 1] == "0,1"

    assert "-t" in cmd2
    assert cmd2[cmd2.index("-t") + 1] == "200,400"

    assert "-j" in cmd2
    assert cmd2[cmd2.index("-j") + 1] == "1:2,2:2"

    assert "-x" in cmd2


@patch("subprocess.Popen")
def test_upscale_directory_success(mock_popen, tmp_path: Path):
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "1.png").touch()

    out_dir = tmp_path / "out"

    # Mock subprocess.Popen
    mock_process = MagicMock()
    mock_process.poll.side_effect = [None, 0]  # Returns None once (running), then 0 (done)
    mock_process.returncode = 0

    # Mock stdout to provide a dummy stream for _drain_stdout
    mock_stdout = MagicMock()
    mock_stdout.readline.side_effect = [b"10.00%", b""]
    mock_process.stdout = mock_stdout

    mock_popen.return_value = mock_process

    upscaler = RealEsrganUpscaler(RealEsrganSettings())
    upscaler.upscale_directory(in_dir, out_dir)

    mock_popen.assert_called_once()

    # Ensure stdout was closed
    mock_stdout.close.assert_called_once()


@patch("subprocess.Popen")
def test_upscale_directory_failure(mock_popen, tmp_path: Path):
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "1.png").touch()

    out_dir = tmp_path / "out"

    mock_process = MagicMock()
    mock_process.poll.return_value = 1  # Finished immediately with error
    mock_process.returncode = 1

    mock_stdout = MagicMock()
    mock_stdout.readline.side_effect = [b"Error message", b""]
    mock_process.stdout = mock_stdout

    mock_popen.return_value = mock_process

    upscaler = RealEsrganUpscaler(RealEsrganSettings())

    with pytest.raises(RealEsrganError, match="exited with code 1"):
        upscaler.upscale_directory(in_dir, out_dir)
