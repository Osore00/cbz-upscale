"""Base interface for all upscaler backends."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from cbz_upscale.config import UpscalerSettings

class BaseUpscaler(ABC):
    """Contract that every upscaler backend must implement."""
    
    # Must be defined by subclasses
    name: ClassVar[str]
    settings_class: ClassVar[type[UpscalerSettings]]
    
    def __init__(self, settings: UpscalerSettings):
        """Initialize with backend-specific settings."""
        self.settings = settings
        
    @abstractmethod
    def validate_environment(self) -> None:
        """Check if the required executable/dependencies are available.
        
        Raises:
            Exception: If validation fails (e.g., FileNotFoundError).
        """
        pass
        
    @abstractmethod
    def upscale_directory(
        self,
        input_dir: Path,
        output_dir: Path,
        *,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        """Upscale all images from input_dir and save to output_dir.
        
        Args:
            input_dir: Directory containing original images
            output_dir: Directory where upscaled images should be saved
            progress_callback: Optional callback receiving (current_file, total_files)
        """
        pass
