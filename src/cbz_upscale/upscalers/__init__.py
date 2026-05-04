"""Plugin system for upscaler backends.

Importing this module triggers the registration of all included backends.
"""

from cbz_upscale.upscalers._base import BaseUpscaler
from cbz_upscale.upscalers._registry import UpscalerRegistry

# Backends will be imported here in the next steps
from . import dummy

__all__ = ["BaseUpscaler", "UpscalerRegistry"]
