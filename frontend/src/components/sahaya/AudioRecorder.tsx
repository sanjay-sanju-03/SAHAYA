"use client";

import { useState, useRef } from "react";
import { Mic, Square, Loader2 } from "lucide-react";

interface AudioRecorderProps {
  onAudioReady: (blob: Blob) => Promise<void>;
  isTranscribing: boolean;
}

export function AudioRecorder({ onAudioReady, isTranscribing }: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<BlobPart[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });

      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data);
      };

      mediaRecorder.current.onstop = async () => {
        const blob = new Blob(chunks.current, { type: 'audio/webm' });
        chunks.current = [];
        await onAudioReady(blob);
      };

      chunks.current = [];
      mediaRecorder.current.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Microphone access denied", err);
      alert("Microphone access is required to use voice input.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorder.current && isRecording) {
      mediaRecorder.current.stop();
      setIsRecording(false);
      mediaRecorder.current.stream.getTracks().forEach(t => t.stop());
    }
  };

  if (isTranscribing) {
    return (
      <button disabled className="btn-secondary w-full recorder-idle opacity-50 justify-center">
        <Loader2 className="w-5 h-5 animate-spin" />
        Transcribing audio...
      </button>
    );
  }

  if (isRecording) {
    return (
      <button
        onClick={stopRecording}
        className="btn-secondary w-full recorder-active justify-center font-bold text-blocked-700"
      >
        <div className="relative flex items-center justify-center w-5 h-5 mr-2">
          <Square className="w-4 h-4 fill-blocked-600 text-blocked-600 relative z-10" />
          <div className="absolute inset-0 bg-blocked-400 rounded-full recording-pulse"></div>
        </div>
        Stop Recording
      </button>
    );
  }

  return (
    <button
      onClick={startRecording}
      className="btn-secondary w-full recorder-idle justify-center font-bold text-navy-700"
    >
      <Mic className="w-5 h-5 mr-2 text-navy-600" />
      Speak (Malayalam or English)
    </button>
  );
}
