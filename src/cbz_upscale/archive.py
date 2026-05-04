"""Archive handler for CBZ extraction and repackaging."""

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

# Standard image extensions supported by upscalers
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"})

@dataclass(frozen=True)
class ExtractResult:
    """Result of extracting and classifying a CBZ archive."""
    image_dir: Path
    meta_dir: Path
    image_count: int
    meta_count: int

class ArchiveError(Exception):
    """Exception raised for archive-related errors."""
    pass

class ArchiveHandler:
    """Handles extracting and repackaging CBZ archives with content classification."""
    
    def extract(self, cbz_path: Path, work_dir: Path) -> ExtractResult:
        """Extract CBZ, physically separating images and metadata.
        
        Args:
            cbz_path: Path to the source .cbz file
            work_dir: Temporary directory to extract into
            
        Returns:
            ExtractResult with paths to the separated directories
            
        Raises:
            ArchiveError: If the archive is invalid or extraction fails
        """
        if not cbz_path.exists():
            raise ArchiveError(f"File not found: {cbz_path}")
            
        image_dir = work_dir / "images"
        meta_dir = work_dir / "meta"
        
        image_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)
        
        image_count = 0
        meta_count = 0
        
        try:
            with zipfile.ZipFile(cbz_path, "r") as zf:
                for entry in zf.infolist():
                    if entry.is_dir():
                        continue
                        
                    is_image = self._is_image(entry.filename)
                    target_dir = image_dir if is_image else meta_dir
                    
                    # We want to preserve the relative path inside the zip 
                    # so that when we repack, it goes back to the right place.
                    target_path = target_dir / entry.filename
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with zf.open(entry) as source, open(target_path, "wb") as dest:
                        shutil.copyfileobj(source, dest)
                        
                    if is_image:
                        image_count += 1
                    else:
                        meta_count += 1
                        
        except zipfile.BadZipFile as e:
            raise ArchiveError(f"Invalid ZIP archive: {e}") from e
        except Exception as e:
            raise ArchiveError(f"Failed to extract archive: {e}") from e
            
        return ExtractResult(
            image_dir=image_dir,
            meta_dir=meta_dir,
            image_count=image_count,
            meta_count=meta_count,
        )

    def repack(self, image_dir: Path, meta_dir: Path, output_path: Path) -> Path:
        """Repack upscaled images and original metadata back into a CBZ.
        
        Args:
            image_dir: Directory containing the upscaled images
            meta_dir: Directory containing the original metadata (ComicInfo.xml, etc.)
            output_path: Where to save the new .cbz file
            
        Returns:
            Path to the created .cbz file
            
        Raises:
            ArchiveError: If repacking fails
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                # 1. Add metadata files first
                if meta_dir.exists():
                    for file_path in meta_dir.rglob("*"):
                        if file_path.is_file():
                            # Path relative to the root of meta_dir
                            arcname = file_path.relative_to(meta_dir)
                            zf.write(file_path, arcname)
                            
                # 2. Add images, sorted alphabetically
                if image_dir.exists():
                    image_files = sorted(f for f in image_dir.rglob("*") if f.is_file())
                    for file_path in image_files:
                        arcname = file_path.relative_to(image_dir)
                        zf.write(file_path, arcname)
                        
        except Exception as e:
            if output_path.exists():
                output_path.unlink()  # Clean up partial file on failure
            raise ArchiveError(f"Failed to repack archive: {e}") from e
            
        return output_path

    @staticmethod
    def _is_image(filename: str) -> bool:
        """Check if a filename corresponds to a supported image format."""
        return Path(filename).suffix.lower() in IMAGE_EXTENSIONS
