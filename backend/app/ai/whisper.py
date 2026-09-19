"""
SAHAYA — Whisper transcription wrapper.
Gracefully falls back to empty string if API key is missing.
"""
from __future__ import annotations

import logging
import os

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        self._client = AsyncOpenAI(api_key=api_key) if api_key else None

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """
        Transcribe audio bytes using OpenAI Whisper.
        Returns empty string if unavailable (caller shows fallback UI).
        """
        if self._client is None:
            logger.warning("Whisper: OpenAI client unavailable.")
            return ""
        try:
            import io
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = filename

            response = await self._client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
                prompt=(
                    "This is an emergency report spoken in Malayalam or English. "
                    "Transcribe it faithfully, preserving names, places, and accessibility needs."
                ),
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            return ""


transcriber = WhisperTranscriber()
