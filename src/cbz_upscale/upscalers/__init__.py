"""Plugin system for upscaler backends.

Importing this module triggers the registration of all included backends.
"""

from cbz_upscale.upscalers._base import BaseUpscaler
from cbz_upscale.upscalers._registry import UpscalerRegistry

# Import backends to trigger their @UpscalerRegistry.register decorators
from . import dummy
from . import realesrgan

__all__ = ["BaseUpscaler", "UpscalerRegistry"]
