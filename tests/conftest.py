import zipfile
from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def sample_cbz(tmp_path: Path) -> Path:
    """Create a sample CBZ file with some images and metadata."""
    cbz_path = tmp_path / "sample.cbz"

    # Create a temporary directory to build the contents
    build_dir = tmp_path / "build"
    build_dir.mkdir()

    # Create some sample images
    images_dir = build_dir / "images"
    images_dir.mkdir()

    for i in range(1, 4):
        img_path = images_dir / f"page_{i:03d}.png"
        # Create a tiny 10x10 black image
        img = Image.new("RGB", (10, 10), color="black")
        img.save(img_path)

    # Create a subfolder with an image to test recursive extraction
    sub_dir = images_dir / "chapter_2"
    sub_dir.mkdir()
    img = Image.new("RGB", (10, 10), color="red")
    img.save(sub_dir / "page_004.jpg")

    # Create sample metadata
    meta_path = build_dir / "ComicInfo.xml"
    meta_path.write_text("<?xml version='1.0'?><ComicInfo><Title>Sample</Title></ComicInfo>")

    # Zip it up
    with zipfile.ZipFile(cbz_path, "w") as zf:
        for file_path in build_dir.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(build_dir))

    return cbz_path
