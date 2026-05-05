"""Pipeline orchestrator for the extract-upscale-repack workflow."""

import shutil
import tempfile
import time
from pathlib import Path

from cbz_upscale.archive import ArchiveError, ArchiveHandler
from cbz_upscale.config import AppConfig
from cbz_upscale.console import (
    console,
    create_progress,
    print_error,
    print_summary,
    step_status,
)
from cbz_upscale.upscalers import UpscalerRegistry


class PipelineError(Exception):
    """Exception raised for errors during the upscale pipeline."""

    pass


class UpscalePipeline:
    """Orchestrates the full workflow: extract -> upscale -> repack."""

    def __init__(self, config: AppConfig):
        """Initialize the pipeline with the given configuration.

        Args:
            config: The application configuration.
        """
        self.config = config
        self.archive = ArchiveHandler()

        try:
            upscaler_cls = UpscalerRegistry.get(config.upscaler)
            self.upscaler = upscaler_cls(settings=config.get_upscaler_settings())
        except KeyError as e:
            raise PipelineError(str(e)) from e

    def _resolve_output_path(self, cbz_path: Path) -> Path:
        """Determine the final output path for the upscaled CBZ.

        Args:
            cbz_path: Path to the original CBZ file.

        Returns:
            The path where the new CBZ should be saved.
        """
        if self.config.output:
            if self.config.output.is_dir() or not self.config.output.suffix:
                # Output is a directory, keep original stem + suffix
                return self.config.output / f"{cbz_path.stem}{self.config.suffix}.cbz"
            else:
                # Output is a specific file path
                return self.config.output

        # Default: next to original file with suffix
        return cbz_path.with_name(f"{cbz_path.stem}{self.config.suffix}.cbz")

    def process_file(self, cbz_path: Path) -> Path | None:
        """Process a single CBZ file through the full pipeline.

        Args:
            cbz_path: Path to the CBZ file to process.

        Returns:
            Path to the output CBZ file, or None if an error occurred.
        """
        console.print(f"\n[bold]Processing:[/bold] {cbz_path.name}")
        output_path = self._resolve_output_path(cbz_path)

        # Create a parent directory for the temp dir in the same location as output
        # (or input if no output defined) to avoid cross-drive extraction issues
        temp_parent = output_path.parent if self.config.output else cbz_path.parent
        temp_parent.mkdir(parents=True, exist_ok=True)

        work_dir = Path(tempfile.mkdtemp(prefix="cbz_upscale_", dir=temp_parent))
        output_images_dir = work_dir / "upscaled"

        try:
            # Step 1: Extract archive
            with step_status("Extracting archive") as _:
                extract_result = self.archive.extract(cbz_path, work_dir)
                console.print(
                    f"[dim] ({extract_result.image_count} images, "
                    f"{extract_result.meta_count} meta files)[/dim]",
                    end="",
                )

            if extract_result.image_count == 0:
                print_error("No images found in the archive.")
                return None

            # Step 2: Upscale images
            console.print("  [step.pending]├─[/step.pending] Upscaling images...")
            with create_progress() as progress:
                task_id = progress.add_task(
                    "Upscaling...",
                    total=extract_result.image_count,
                )

                def update_progress(current: int, total: int) -> None:
                    progress.update(task_id, completed=current, total=total)

                self.upscaler.upscale_directory(
                    input_dir=extract_result.image_dir,
                    output_dir=output_images_dir,
                    progress_callback=update_progress,
                )
            console.print("  [step.done]├─ ✓[/step.done] Upscaling images complete")

            # Step 3: Repack archive
            with step_status("Repacking archive"):
                self.archive.repack(
                    image_dir=output_images_dir,
                    meta_dir=extract_result.meta_dir,
                    output_path=output_path,
                )

            # Step 5: Cleanup (handled by finally block, but we can log it here)
            if not self.config.keep_temp:
                with step_status("Cleaning up"):
                    pass # actual cleanup in finally block

            return output_path

        except (ArchiveError, PipelineError) as e:
            print_error(str(e))
            return None
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            if self.config.verbose:
                console.print_exception()
            return None
        finally:
            if not self.config.keep_temp and work_dir.exists():
                try:
                    shutil.rmtree(work_dir)
                except OSError as e:
                    print_error(f"Failed to remove temporary directory {work_dir}: {e}")
            elif self.config.keep_temp:
                console.print(f"  [info]i[/info] Keeping temp directory: {work_dir}")

    def process_batch(self, input_path: Path) -> list[Path]:
        """Process a single file or all CBZ files in a directory.

        Args:
            input_path: Path to a CBZ file or a directory containing CBZ files.

        Returns:
            List of paths to successfully processed output files.
        """
        start_time = time.time()
        successful_outputs: list[Path] = []

        if not input_path.exists():
            print_error(f"Input path does not exist: {input_path}")
            return []

        if input_path.is_file():
            if input_path.suffix.lower() != ".cbz":
                print_error(f"Input file must be a .cbz archive: {input_path}")
                return []
            files_to_process = [input_path]
        else:
            files_to_process = sorted(
                f for f in input_path.iterdir() if f.is_file() and f.suffix.lower() == ".cbz"
            )
            if not files_to_process:
                print_error(f"No .cbz files found in directory: {input_path}")
                return []
            console.print(f"Found {len(files_to_process)} archives to process.")

        # Validate environment ONCE before processing any files
        try:
            with step_status("Validating upscaler environment"):
                self.upscaler.validate_environment()
        except Exception as e:
            print_error(str(e))
            return []

        for cbz_file in files_to_process:
            result = self.process_file(cbz_file)
            if result:
                successful_outputs.append(result)

        total_time = time.time() - start_time
        print_summary(len(successful_outputs), total_time)

        return successful_outputs
