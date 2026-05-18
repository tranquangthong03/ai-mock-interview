"""
Unit tests for audio_processing_service.
"""

import pytest
from unittest.mock import MagicMock

from app.services.audio_processing_service import (
    AudioProcessingError,
    FFMPEG_REQUIRED_MESSAGE,
    compute_speech_metrics,
    convert_audio_to_wav_16k_mono,
    process_audio_answer,
    save_upload_audio_file,
    transcribe_audio,
)


class TestComputeSpeechMetrics:
    """Tests for compute_speech_metrics."""

    def test_basic_transcript(self):
        transcript = "Em da xay dung mot REST API bang FastAPI cho he thong quan ly sinh vien."
        result = compute_speech_metrics(transcript)

        assert result["word_count"] > 0
        assert result["speech_rate_wpm"] > 0
        assert isinstance(result["filler_words"], list)
        assert isinstance(result["notes"], list)

    def test_detects_filler_words(self):
        transcript = "Um em nghi la uh kieu nhu em dung FastAPI noi chung la tot"
        result = compute_speech_metrics(transcript)

        assert result["filler_word_count"] > 0
        assert len(result["filler_words"]) > 0

    def test_handles_empty_transcript(self):
        result = compute_speech_metrics("")
        assert result["word_count"] == 0
        assert result["speech_rate_wpm"] == 0
        assert "Transcript" in result["notes"][0]

    def test_handles_none_transcript(self):
        result = compute_speech_metrics(None)
        assert result["word_count"] == 0

    def test_with_audio_duration(self):
        transcript = "Em da xay dung REST API bang FastAPI."
        result = compute_speech_metrics(transcript, audio_duration_seconds=10.0)
        assert result["duration_seconds"] == 10.0
        assert result["speech_rate_wpm"] > 0

    def test_fast_speech_note(self):
        transcript = " ".join(["word"] * 100)
        result = compute_speech_metrics(transcript, audio_duration_seconds=15.0)
        assert any("nhanh" in n for n in result["notes"])


class TestSaveUploadAudioFile:
    """Tests for save_upload_audio_file."""

    def test_rejects_invalid_extension(self):
        mock_file = MagicMock()
        mock_file.filename = "test.exe"
        mock_file.content_type = "application/octet-stream"
        mock_file.file = MagicMock()

        with pytest.raises(AudioProcessingError, match="not supported"):
            save_upload_audio_file(mock_file, session_id=1)

    def test_rejects_txt_extension(self):
        mock_file = MagicMock()
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"
        mock_file.file = MagicMock()

        with pytest.raises(AudioProcessingError, match="not supported"):
            save_upload_audio_file(mock_file, session_id=1)

    def test_rejects_empty_audio_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "app.services.audio_processing_service.AUDIO_UPLOAD_DIR",
            tmp_path,
        )

        mock_file = MagicMock()
        mock_file.filename = "empty.webm"
        mock_file.content_type = "audio/webm"
        mock_file.file.read.return_value = b""

        with pytest.raises(AudioProcessingError, match="empty"):
            save_upload_audio_file(mock_file, session_id=1)


class TestProcessAudioAnswer:
    """Tests for process_audio_answer with mocked transcription."""

    def test_process_with_mock_stt(self, tmp_path, monkeypatch):
        monkeypatch.setenv("STT_PROVIDER", "mock")
        monkeypatch.setattr(
            "app.services.audio_processing_service.AUDIO_UPLOAD_DIR",
            tmp_path,
        )

        mock_file = MagicMock()
        mock_file.filename = "answer.webm"
        mock_file.content_type = "audio/webm"
        mock_file.file.read.return_value = b"fake audio content"

        result = process_audio_answer(mock_file, session_id=42)

        assert "transcript" in result
        assert "speech_metrics" in result
        assert "audio_file_path" in result
        assert len(result["transcript"]) > 0
        assert result["speech_metrics"]["word_count"] > 0

    def test_mock_stt_does_not_require_ffmpeg(self, tmp_path, monkeypatch):
        monkeypatch.setenv("STT_PROVIDER", "mock")
        monkeypatch.setattr("app.services.audio_processing_service.shutil.which", lambda _: None)
        audio_path = tmp_path / "answer.webm"
        audio_path.write_bytes(b"fake audio content")

        transcript = transcribe_audio(audio_path)

        assert "measuring latency" in transcript

    @pytest.mark.parametrize("provider", ["whisper", "faster-whisper"])
    def test_real_stt_without_ffmpeg_returns_clear_error(self, tmp_path, monkeypatch, provider):
        monkeypatch.setenv("STT_PROVIDER", provider)
        monkeypatch.setattr("app.services.audio_processing_service.shutil.which", lambda _: None)
        audio_path = tmp_path / "answer.webm"
        audio_path.write_bytes(b"fake audio content")

        with pytest.raises(AudioProcessingError) as exc:
            transcribe_audio(audio_path)

        assert exc.value.status_code == 503
        assert FFMPEG_REQUIRED_MESSAGE in exc.value.message

    def test_missing_audio_file_returns_clear_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("STT_PROVIDER", "mock")

        with pytest.raises(AudioProcessingError) as exc:
            transcribe_audio(tmp_path / "missing.webm")

        assert exc.value.status_code == 400
        assert "does not exist" in exc.value.message


class TestAudioConversion:
    """Tests for ffmpeg conversion before real STT."""

    def test_webm_is_converted_to_wav_16k_mono(self, tmp_path, monkeypatch):
        input_path = tmp_path / "answer.webm"
        input_path.write_bytes(b"fake webm audio")
        calls = {}

        def fake_run(cmd, capture_output, text, check):
            calls["cmd"] = cmd
            output_path = tmp_path / "answer.wav"
            output_path.write_bytes(b"fake wav audio")

            class Result:
                returncode = 0
                stderr = ""

            return Result()

        monkeypatch.setattr("app.services.audio_processing_service.shutil.which", lambda _: "ffmpeg")
        monkeypatch.setattr("app.services.audio_processing_service.subprocess.run", fake_run)

        output = convert_audio_to_wav_16k_mono(input_path)

        assert output == tmp_path / "answer.wav"
        assert output.exists()
        assert output.stat().st_size > 0
        assert calls["cmd"][:4] == ["ffmpeg", "-y", "-i", str(input_path)]
        assert "-ac" in calls["cmd"]
        assert "1" in calls["cmd"]
        assert "-ar" in calls["cmd"]
        assert "16000" in calls["cmd"]

    def test_conversion_without_ffmpeg_returns_clear_error(self, tmp_path, monkeypatch):
        input_path = tmp_path / "answer.webm"
        input_path.write_bytes(b"fake webm audio")
        monkeypatch.setattr("app.services.audio_processing_service.shutil.which", lambda _: None)

        with pytest.raises(AudioProcessingError) as exc:
            convert_audio_to_wav_16k_mono(input_path)

        assert exc.value.status_code == 503
        assert FFMPEG_REQUIRED_MESSAGE in exc.value.message

    def test_conversion_empty_output_returns_clear_error(self, tmp_path, monkeypatch):
        input_path = tmp_path / "answer.webm"
        input_path.write_bytes(b"fake webm audio")

        def fake_run(cmd, capture_output, text, check):
            output_path = tmp_path / "answer.wav"
            output_path.write_bytes(b"")

            class Result:
                returncode = 0
                stderr = ""

            return Result()

        monkeypatch.setattr("app.services.audio_processing_service.shutil.which", lambda _: "ffmpeg")
        monkeypatch.setattr("app.services.audio_processing_service.subprocess.run", fake_run)

        with pytest.raises(AudioProcessingError) as exc:
            convert_audio_to_wav_16k_mono(input_path)

        assert exc.value.status_code == 400
        assert "empty file" in exc.value.message
