"use client";

import { ChangeEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createIncident, transcribeAudio } from "@/lib/api";
import { AudioRecorder } from "@/components/sahaya/AudioRecorder";
import { AudioLines, CheckCircle2, CircleHelp, Send, Upload, XCircle } from "lucide-react";

export default function Home() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageName, setImageName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const imageInput = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!text.trim() && !imageUrl) return;

    setIsSubmitting(true);
    setError(null);
    try {
      const reportText = text.trim() || "An incident image was attached. Review visual observations carefully and request clarification for any unknown accessibility requirements.";
      const incident = await createIncident(reportText, imageUrl || undefined);
      router.push(`/processing?id=${incident.id}`);
    } catch (err: unknown) {
      console.error(err);
      setError("Failed to create incident. Please check the backend connection.");
      setIsSubmitting(false);
    }
  };

  const handleImage = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("Please choose an image file.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("Please choose an image smaller than 5 MB.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setImageUrl(reader.result as string);
      setImageName(file.name);
      setError(null);
    };
    reader.onerror = () => setError("The selected image could not be read.");
    reader.readAsDataURL(file);
  };

  const clearImage = () => {
    setImageUrl(null);
    setImageName(null);
    if (imageInput.current) imageInput.current.value = "";
  };

  const handleDemo = () => {
    // Demo mode explicitly skips creating a new incident and uses the pre-extracted demo case
    router.push(`/incident/demo-001/review`);
  };

  const handleAudioReady = async (blob: Blob) => {
    setIsTranscribing(true);
    setError(null);
    try {
      const res = await transcribeAudio(blob);
      if (res.success) {
        setText(res.transcript);
      } else {
        setError(res.message);
      }
    } catch {
      setError("Audio transcription failed.");
    } finally {
      setIsTranscribing(false);
    }
  };

  return (
    <div className="surface-grid min-h-[calc(100vh-64px)]">
    <div className="page-container flex flex-col items-center justify-center min-h-[calc(100vh-64px)]">

      <div className="text-center max-w-2xl mx-auto mb-10 reveal">
        <p className="metric-label text-teal-700 mb-3">INCLUSIVE EMERGENCY DECISION ENGINE</p>
        <h1 className="text-display text-navy-950 mb-4 text-4xl sm:text-5xl">
          Calm under pressure.<br/>Precise when it matters.
        </h1>
        <p className="text-xl text-gray-500">
          Before we send help, let&apos;s make sure it can actually help.
        </p>
      </div>

      <div className="w-full max-w-xl mb-6 grid sm:grid-cols-2 gap-3 text-left">
        <div className="rounded-xl bg-gray-100 p-4 text-gray-600 text-sm">
          <p className="font-semibold text-gray-800 mb-1">Traditional matching asks</p>
          <p>“Is this resource available?”</p>
        </div>
        <div className="rounded-xl bg-navy-50 p-4 text-navy-700 text-sm border border-navy-100">
          <p className="font-semibold text-navy-900 mb-1">SAHAYA asks</p>
          <p>“Is this resource compatible with this person?”</p>
        </div>
      </div>

      <div className="card w-full max-w-xl p-6 sm:p-8 reveal reveal-delay-2">
        {error && (
          <div className="bg-blocked-50 text-blocked-700 p-4 rounded-lg mb-6 border border-blocked-200">
            {error}
          </div>
        )}

        <div className="flex gap-4 mb-6">
          <AudioRecorder onAudioReady={handleAudioReady} isTranscribing={isTranscribing} />
          <input ref={imageInput} type="file" accept="image/png,image/jpeg,image/webp" onChange={handleImage} className="hidden" />
          <button type="button" onClick={() => imageInput.current?.click()} className="btn-secondary w-full justify-center">
            <Upload className="w-5 h-5 mr-2 text-navy-600" />
            {imageName ? "Change Incident Image" : "Add Incident Image"}
          </button>
        </div>

        {imageUrl && (
          <div className="mb-5 rounded-xl border border-gray-200 overflow-hidden bg-gray-50">
            {/* Local preview only; the image is sent with the incident when analyzed. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={imageUrl} alt="Selected incident" className="w-full max-h-56 object-cover" />
            <div className="flex items-center justify-between gap-3 p-3 text-sm">
              <span className="truncate text-gray-600">{imageName}</span>
              <button type="button" onClick={clearImage} className="text-blocked-700 font-semibold shrink-0">Remove</button>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Describe what is happening..."
            className="w-full h-40 p-4 border rounded-xl text-lg mb-4 focus:ring-2 focus:ring-navy-400 outline-none resize-none font-ml"
            disabled={isSubmitting || isTranscribing}
          />
          <button
            type="submit"
            className="btn-primary w-full text-lg py-4"
            disabled={(!text.trim() && !imageUrl) || isSubmitting || isTranscribing}
          >
            {isSubmitting ? "Analyzing Incident..." : (
              <>
                Analyze Incident
                <Send className="w-5 h-5 ml-2" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t text-center">
          <button onClick={handleDemo} className="btn-secondary text-sm">
            <AudioLines className="w-4 h-4" />
            Try Guided Demo
          </button>
          <p className="text-xs text-gray-500 mt-2">Uses seeded synthetic data. No real emergency dispatch.</p>
        </div>
      </div>

      <div className="w-full max-w-xl grid grid-cols-3 gap-3 mt-6 reveal reveal-delay-3">
        <div className="metric-card text-center"><CheckCircle2 className="w-5 h-5 mx-auto text-safe-600 mb-1" /><p className="metric-label">SAFE</p><p className="text-sm text-gray-600">Verified</p></div>
        <div className="metric-card text-center"><CircleHelp className="w-5 h-5 mx-auto text-unknown-600 mb-1" /><p className="metric-label">UNKNOWN</p><p className="text-sm text-gray-600">Check first</p></div>
        <div className="metric-card text-center"><XCircle className="w-5 h-5 mx-auto text-blocked-600 mb-1" /><p className="metric-label">BLOCKED</p><p className="text-sm text-gray-600">Conflict found</p></div>
      </div>
      <p className="mt-5 text-sm font-semibold text-navy-600 tracking-wide">AI understands <span className="text-teal-600">→</span> Rules verify <span className="text-teal-600">→</span> Humans decide</p>

    </div>
    </div>
  );
}
