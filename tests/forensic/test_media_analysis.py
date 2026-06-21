"""Unit tests for media analysis functionality."""

import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from forensic.media.detector import detect_media_type
from forensic.media.metadata import (
    extract_image_metadata,
    extract_video_metadata,
    extract_audio_metadata,
    extract_media_metadata
)


def test_detect_media_type_images():
    """Test detection of image file types."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test JPEG
        jpg_path = Path(temp_dir) / "test.jpg"
        jpg_path.touch()
        assert detect_media_type(jpg_path) == "image"

        # Test PNG
        png_path = Path(temp_dir) / "test.png"
        png_path.touch()
        assert detect_media_type(png_path) == "image"

        # Test GIF
        gif_path = Path(temp_dir) / "test.gif"
        gif_path.touch()
        assert detect_media_type(gif_path) == "image"


def test_detect_media_type_videos():
    """Test detection of video file types."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test MP4
        mp4_path = Path(temp_dir) / "test.mp4"
        mp4_path.touch()
        assert detect_media_type(mp4_path) == "video"

        # Test AVI
        avi_path = Path(temp_dir) / "test.avi"
        avi_path.touch()
        assert detect_media_type(avi_path) == "video"

        # Test MOV
        mov_path = Path(temp_dir) / "test.mov"
        mov_path.touch()
        assert detect_media_type(mov_path) == "video"


def test_detect_media_type_audio():
    """Test detection of audio file types."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test MP3
        mp3_path = Path(temp_dir) / "test.mp3"
        mp3_path.touch()
        assert detect_media_type(mp3_path) == "audio"

        # Test WAV
        wav_path = Path(temp_dir) / "test.wav"
        wav_path.touch()
        assert detect_media_type(wav_path) == "audio"

        # Test FLAC
        flac_path = Path(temp_dir) / "test.flac"
        flac_path.touch()
        assert detect_media_type(flac_path) == "audio"


def test_detect_media_type_documents():
    """Test detection of document file types."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test PDF
        pdf_path = Path(temp_dir) / "test.pdf"
        pdf_path.touch()
        assert detect_media_type(pdf_path) == "document"

        # Test DOC
        doc_path = Path(temp_dir) / "test.doc"
        doc_path.touch()
        assert detect_media_type(doc_path) == "document"

        # Test TXT
        txt_path = Path(temp_dir) / "test.txt"
        txt_path.touch()
        assert detect_media_type(txt_path) == "document"


def test_detect_media_type_other():
    """Test detection of other/unknown file types."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test unknown extension
        unknown_path = Path(temp_dir) / "test.xyz"
        unknown_path.touch()
        assert detect_media_type(unknown_path) == "other"

        # Test no extension
        no_ext_path = Path(temp_dir) / "test"
        no_ext_path.touch()
        assert detect_media_type(no_ext_path) == "other"


def test_detect_media_type_nonexistent():
    """Test detection of nonexistent files."""
    nonexistent_path = Path("/nonexistent/file.txt")
    assert detect_media_type(nonexistent_path) is None


def test_extract_image_metadata_without_pil():
    """Test image metadata extraction when PIL is not available."""
    with patch('forensic.media.metadata.PIL_AVAILABLE', False):
        with tempfile.TemporaryDirectory() as temp_dir:
            img_path = Path(temp_dir) / "test.jpg"
            img_path.touch()

            result = extract_image_metadata(img_path)
            assert result == {"width": None, "height": None, "exif_data": {}}


def test_extract_image_metadata_nonexistent():
    """Test image metadata extraction for nonexistent file."""
    nonexistent_path = Path("/nonexistent/image.jpg")
    result = extract_image_metadata(nonexistent_path)
    assert result == {"width": None, "height": None, "exif_data": {}}


def test_extract_video_metadata():
    """Test video metadata extraction (placeholder implementation)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = Path(temp_dir) / "test.mp4"
        video_path.touch()

        result = extract_video_metadata(video_path)
        assert result == {
            "width": None,
            "height": None,
            "duration": None
        }


def test_extract_audio_metadata():
    """Test audio metadata extraction (placeholder implementation)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = Path(temp_dir) / "test.mp3"
        audio_path.touch()

        result = extract_audio_metadata(audio_path)
        assert result == {
            "duration": None
        }


def test_extract_media_metadata_dispatch():
    """Test that extract_media_metadata dispatches to correct function based on media type."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test image dispatch
        img_path = Path(temp_dir) / "test.jpg"
        img_path.touch()

        with patch('forensic.media.metadata.extract_image_metadata') as mock_img:
            mock_img.return_value = {"width": 800, "height": 600, "exif_data": {}}
            result = extract_media_metadata(img_path, "image")
            mock_img.assert_called_once_with(img_path)
            assert result == {"width": 800, "height": 600, "exif_data": {}}

        # Test video dispatch
        vid_path = Path(temp_dir) / "test.mp4"
        vid_path.touch()

        with patch('forensic.media.metadata.extract_video_metadata') as mock_vid:
            mock_vid.return_value = {"width": 1920, "height": 1080, "duration": 120.5}
            result = extract_media_metadata(vid_path, "video")
            mock_vid.assert_called_once_with(vid_path)
            assert result == {"width": 1920, "height": 1080, "duration": 120.5}

        # Test audio dispatch
        aud_path = Path(temp_dir) / "test.mp3"
        aud_path.touch()

        with patch('forensic.media.metadata.extract_audio_metadata') as mock_aud:
            mock_aud.return_value = {"duration": 180.0}
            result = extract_media_metadata(aud_path, "audio")
            mock_aud.assert_called_once_with(aud_path)
            assert result == {"duration": 180.0}

        # Test document dispatch (returns empty dict)
        doc_path = Path(temp_dir) / "test.pdf"
        doc_path.touch()

        result = extract_media_metadata(doc_path, "document")
        assert result == {}


if __name__ == "__main__":
    test_detect_media_type_images()
    test_detect_media_type_videos()
    test_detect_media_type_audio()
    test_detect_media_type_documents()
    test_detect_media_type_other()
    test_detect_media_type_nonexistent()
    test_extract_image_metadata_without_pil()
    test_extract_image_metadata_nonexistent()
    test_extract_video_metadata()
    test_extract_audio_metadata()
    test_extract_media_metadata_dispatch()
    print("All tests passed!")