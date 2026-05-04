"""Dummy upscaler backend for testing the pipeline without GPU usage."""

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from cbz_upscale.config import DummySettings
from cbz_upscale.upscalers._base import BaseUpscaler
from cbz_upscale.upscalers._registry import UpscalerRegistry

@UpscalerRegistry.register
class DummyUpscaler(BaseUpscaler):
    """A test backend that simply copies and renames images without upscaling."""
    
    name: ClassVar[str] = "dummy"
    settings_class: ClassVar[type] = DummySettings
    
    # We must explicitly define the type for self.settings since BaseUpscaler 
    # typed it generically.
    settings: DummySettings

    def validate_environment(self) -> None:
        """The dummy backend has no external dependencies."""
        pass

    def upscale_directory(
        self,
        input_dir: Path,
        output_dir: Path,
        *,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        """Copy images to output_dir with formatted names.
        
        This mimics the behavior of a real upscaler but executes instantly.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Collect all files (assuming the archive handler only put images here)
        images = sorted(f for f in input_dir.rglob("*") if f.is_file())
        total_images = len(images)
        
        if total_images == 0:
            return
            
        current_number = self.settings.start_number
        
        for i, image_path in enumerate(images, start=1):
            # Generate new filename using the settings
            # e.g. "page_001.png"
            new_name = (
                f"{self.settings.prefix}_"
                f"{current_number:0{self.settings.zero_padding}d}"
                f".{self.settings.output_format}"
            )
            
            # Since the original files might be in subdirectories, we flatten them 
            # or keep structure? Most upscalers flatten or expect specific output.
            # For this simple tool, we'll just put them in the root of output_dir.
            dest_path = output_dir / new_name
            
            # Perform the "upscale" (copy)
            shutil.copy2(image_path, dest_path)
            
            current_number += 1
            
            # Report progress if a callback was provided
            if progress_callback:
                progress_callback(i, total_images)
