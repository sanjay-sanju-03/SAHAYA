"""
SAHAYA — Audio transcription API endpoint.
"""
from fastapi import APIRouter, File, UploadFile, HTTPException
from app.ai.whisper import transcriber

router = APIRouter(prefix="/api/audio", tags=["audio"])


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> dict:
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file.")

    audio_bytes = await file.read()
    if len(audio_bytes) > 25 * 1024 * 1024:  # 25MB Whisper limit
        raise HTTPException(status_code=413, detail="Audio file exceeds 25MB limit.")

    text = await transcriber.transcribe(audio_bytes, file.filename or "audio.webm")

    if not text:
        return {
            "success": False,
            "transcript": "",
            "message": "Transcription unavailable. Please type your report.",
        }

    return {"success": True, "transcript": text, "message": ""}
