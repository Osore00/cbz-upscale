import zipfile
from pathlib import Path

import pytest

from cbz_upscale.archive import ArchiveError, ArchiveHandler


def test_archive_handler_extract(sample_cbz: Path, tmp_path: Path):
    handler = ArchiveHandler()
    work_dir = tmp_path / "work"

    result = handler.extract(sample_cbz, work_dir)

    # Check the result object
    assert result.image_count == 4
    assert result.meta_count == 1
    assert result.image_dir == work_dir / "images"
    assert result.meta_dir == work_dir / "meta"

    # Check extracted files
    assert (result.meta_dir / "ComicInfo.xml").exists()
    assert (result.image_dir / "images" / "page_001.png").exists()
    assert (result.image_dir / "images" / "chapter_2" / "page_004.jpg").exists()


def test_archive_handler_extract_invalid_zip(tmp_path: Path):
    bad_cbz = tmp_path / "bad.cbz"
    bad_cbz.write_text("Not a zip file")

    handler = ArchiveHandler()
    work_dir = tmp_path / "work"

    with pytest.raises(ArchiveError, match="File is not a zip file"):
        handler.extract(bad_cbz, work_dir)


def test_archive_handler_repack(sample_cbz: Path, tmp_path: Path):
    handler = ArchiveHandler()

    # 1. Extract first to get the files
    work_dir = tmp_path / "work"
    extract_result = handler.extract(sample_cbz, work_dir)

    # 2. Repack
    output_cbz = tmp_path / "output.cbz"
    result_path = handler.repack(
        image_dir=extract_result.image_dir,
        meta_dir=extract_result.meta_dir,
        output_path=output_cbz,
    )

    assert result_path == output_cbz
    assert output_cbz.exists()
    assert zipfile.is_zipfile(output_cbz)

    # 3. Verify contents of repacked archive
    with zipfile.ZipFile(output_cbz, "r") as zf:
        file_list = zf.namelist()

        # Check all original files are present
        assert "ComicInfo.xml" in file_list
        assert "images/page_001.png" in file_list
        assert "images/chapter_2/page_004.jpg" in file_list

        # Check order: meta files should be first
        assert file_list[0] == "ComicInfo.xml"

        # Images should be sorted
        images = file_list[1:]
        assert images == sorted(images)


def test_archive_handler_classify_entry():
    handler = ArchiveHandler()

    assert handler._is_image("page.png")
    assert handler._is_image("folder/page.JPG")
    assert handler._is_image("image.webp")
    assert handler._is_image("cover.JPEG")

    assert not handler._is_image("ComicInfo.xml")
    assert not handler._is_image("folder/notes.txt")
    assert not handler._is_image("Thumbs.db")
