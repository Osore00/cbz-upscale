"""Registry pattern implementation for dynamically discovering upscaler plugins."""

from typing import ClassVar

from cbz_upscale.upscalers._base import BaseUpscaler

class UpscalerRegistry:
    """Registry for managing available upscaler backends."""
    
    _backends: ClassVar[dict[str, type[BaseUpscaler]]] = {}
    
    @classmethod
    def register(cls, upscaler_cls: type[BaseUpscaler]) -> type[BaseUpscaler]:
        """Decorator to register an upscaler class.
        
        Usage:
            @UpscalerRegistry.register
            class RealEsrganUpscaler(BaseUpscaler):
                name = "realesrgan"
                ...
        """
        if not hasattr(upscaler_cls, "name") or not upscaler_cls.name:
            raise ValueError(f"Cannot register {upscaler_cls.__name__}: missing 'name' attribute")
            
        cls._backends[upscaler_cls.name] = upscaler_cls
        return upscaler_cls
        
    @classmethod
    def get(cls, name: str) -> type[BaseUpscaler]:
        """Get an upscaler class by its registered name."""
        try:
            return cls._backends[name]
        except KeyError:
            available = ", ".join(cls.available())
            raise KeyError(f"Upscaler '{name}' not found. Available: {available}")
            
    @classmethod
    def available(cls) -> list[str]:
        """Get a list of all registered upscaler names."""
        return sorted(cls._backends.keys())
        
    @classmethod
    def get_all(cls) -> dict[str, type[BaseUpscaler]]:
        """Get the full dictionary of registered backends."""
        return cls._backends.copy()
