"""Real-ESRGAN ncnn-vulkan upscaler backend.

Delegates upscaling to the external `realesrgan-ncnn-vulkan` binary via
subprocess. Supports multi-GPU, per-GPU tile sizes, TTA mode, and
configurable threading.
"""

import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from cbz_upscale.archive import IMAGE_EXTENSIONS
from cbz_upscale.config import RealEsrganSettings
from cbz_upscale.upscalers._base import BaseUpscaler
from cbz_upscale.upscalers._registry import UpscalerRegistry

# Interval between output directory polls (seconds)
_POLL_INTERVAL = 0.5


class RealEsrganError(Exception):
    """Exception raised when the Real-ESRGAN process fails."""

    pass


@UpscalerRegistry.register
class RealEsrganUpscaler(BaseUpscaler):
    """Backend that delegates upscaling to realesrgan-ncnn-vulkan."""

    name: ClassVar[str] = "realesrgan"
    settings_class: ClassVar[type] = RealEsrganSettings

    settings: RealEsrganSettings

    def validate_environment(self) -> None:
        """Check that the realesrgan-ncnn-vulkan executable is available.

        Raises:
            RealEsrganError: If the binary cannot be found or executed.
        """
        try:
            result = subprocess.run(
                [self.settings.exe_path, "-h"],
                capture_output=True,
                timeout=15,
            )
            # realesrgan-ncnn-vulkan returns non-zero for -h on some builds,
            # but if we got here the binary exists and is runnable.
            _ = result
        except FileNotFoundError as exc:
            raise RealEsrganError(
                f"Executable not found: '{self.settings.exe_path}'. "
                f"Make sure realesrgan-ncnn-vulkan is installed and available "
                f"in PATH, or provide the full path via --exe-path / config."
            ) from exc
        except subprocess.TimeoutExpired:
            # If -h hangs for 15s something is very wrong, but the binary exists
            pass
        except OSError as exc:
            raise RealEsrganError(
                f"Cannot execute '{self.settings.exe_path}': {exc}"
            ) from exc

    def _build_command(self, input_dir: Path, output_dir: Path) -> list[str]:
        """Build the full command-line argument list for realesrgan-ncnn-vulkan.

        Args:
            input_dir: Directory containing images to upscale.
            output_dir: Directory where upscaled images will be saved.

        Returns:
            List of command-line tokens ready for subprocess.
        """
        s = self.settings
        cmd: list[str] = [
            s.exe_path,
            "-i", str(input_dir),
            "-o", str(output_dir),
            "-s", str(s.scale),
            "-n", s.model,
            "-f", s.output_format,
        ]

        # Multi-GPU support: -g 0,1,2
        if s.gpu_id is not None:
            cmd.extend(["-g", ",".join(str(g) for g in s.gpu_id)])

        # Per-GPU tile size: -t 200 or -t 200,400
        if isinstance(s.tile_size, list):
            cmd.extend(["-t", ",".join(str(t) for t in s.tile_size)])
        elif s.tile_size != 0:
            cmd.extend(["-t", str(s.tile_size)])

        # Thread configuration: -j 1:2:2 or -j 1:2,2:2
        if s.threads:
            cmd.extend(["-j", s.threads])

        # TTA mode: -x flag (no value)
        if s.tta_mode:
            cmd.append("-x")

        return cmd

    def upscale_directory(
        self,
        input_dir: Path,
        output_dir: Path,
        *,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        """Upscale all images from input_dir using realesrgan-ncnn-vulkan.

        Progress is tracked by polling the output directory for completed files.
        This approach is reliable regardless of GPU count — the binary's console
        output (interleaved percentages in multi-GPU mode) is drained in a
        background thread solely to prevent pipe-buffer deadlocks.

        Args:
            input_dir: Directory containing original images.
            output_dir: Directory where upscaled images will be saved.
            progress_callback: Optional callback receiving (current, total).

        Raises:
            RealEsrganError: If the process exits with a non-zero code.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Count input images for progress tracking
        input_images = [
            f for f in input_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        ]
        total = len(input_images)

        if total == 0:
            return

        cmd = self._build_command(input_dir, output_dir)

        # Merge stderr into stdout so we only need one drain thread.
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        # Drain stdout in a background thread to prevent pipe-buffer deadlock.
        # The output is collected for error diagnostics if the process fails.
        captured_output: list[str] = []
        drain_thread = threading.Thread(
            target=self._drain_stdout,
            args=(process, captured_output),
            daemon=True,
        )
        drain_thread.start()

        # Poll output directory for completed files
        try:
            while process.poll() is None:
                if progress_callback:
                    done = self._count_output_files(output_dir)
                    progress_callback(min(done, total), total)
                time.sleep(_POLL_INTERVAL)

            # Final progress update after process exits
            if progress_callback:
                done = self._count_output_files(output_dir)
                progress_callback(min(done, total), total)

        except Exception:
            process.kill()
            process.wait()
            raise
        finally:
            drain_thread.join(timeout=5)

        # Check exit code
        if process.returncode != 0:
            output_text = "".join(captured_output).strip()
            raise RealEsrganError(
                f"realesrgan-ncnn-vulkan exited with code {process.returncode}.\n"
                f"Command: {' '.join(cmd)}\n"
                f"Output: {output_text or '(empty)'}"
            )

    @staticmethod
    def _drain_stdout(
        process: subprocess.Popen[bytes],
        output_lines: list[str],
    ) -> None:
        """Read all stdout from the process to prevent pipe-buffer deadlock.

        Collected lines are appended to *output_lines* for later error reporting.
        """
        assert process.stdout is not None  # guaranteed by Popen(stdout=PIPE)
        for raw_line in iter(process.stdout.readline, b""):
            output_lines.append(raw_line.decode("utf-8", errors="replace"))
        process.stdout.close()

    @staticmethod
    def _count_output_files(output_dir: Path) -> int:
        """Count completed image files in the output directory."""
        return sum(
            1 for f in output_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        )
