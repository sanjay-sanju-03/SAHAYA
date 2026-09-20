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
    <div className="surface-grid min-h-[calc(100vh-64px)] relative">
      <div className="hero-ambient"></div>
      <div className="page-container flex flex-col items-center justify-center min-h-[calc(100vh-64px)] relative z-10 py-12">

        <div className="text-center max-w-3xl mx-auto mb-10 reveal">
          <p className="metric-label text-teal-700 mb-4 tracking-widest uppercase font-bold text-xs">Inclusive Emergency Decision Engine</p>
          <h1 className="text-display text-navy-950 mb-5 text-5xl sm:text-6xl font-extrabold tracking-tight leading-[1.1]">
            Calm under pressure.<br/>Precise when it matters.
          </h1>
          <p className="text-xl sm:text-2xl text-navy-600/80 mb-8 font-medium max-w-2xl mx-auto">
            Before we send help, let&apos;s make sure it can actually help.
          </p>
          <div className="inline-flex items-center text-sm font-semibold text-navy-800 tracking-wide bg-white/80 backdrop-blur-md px-6 py-3 rounded-full shadow-lg shadow-teal-900/5 border border-white/60">
            AI understands <span className="text-teal-500 mx-3">→</span> Rules verify <span className="text-teal-500 mx-3">→</span> Humans decide
          </div>
        </div>

        <div className="w-full max-w-xl mb-10 grid sm:grid-cols-2 gap-5 text-left reveal reveal-delay-1">
          <div className="rounded-2xl bg-white/70 backdrop-blur-xl p-6 text-gray-700 text-sm shadow-xl shadow-navy-900/5 border border-white/60 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl hover:bg-white/90">
            <p className="font-bold text-gray-900 mb-2">Traditional matching asks</p>
            <p className="text-gray-600">“Is this resource available?”</p>
          </div>
          <div className="rounded-2xl bg-white/70 backdrop-blur-xl p-6 text-navy-800 text-sm shadow-xl shadow-navy-900/5 border border-white/60 border-t-[3px] border-t-teal-500 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl hover:bg-white/90">
            <p className="font-bold text-navy-950 mb-2">SAHAYA asks</p>
            <p className="text-navy-700">“Is this resource compatible with this person?”</p>
          </div>
        </div>

        <div className="bg-white/80 backdrop-blur-2xl rounded-[2rem] shadow-2xl shadow-navy-900/10 border border-white p-6 sm:p-10 w-full max-w-xl reveal reveal-delay-2">
          {error && (
            <div className="bg-blocked-50/80 backdrop-blur-md text-blocked-700 p-4 rounded-xl mb-6 border border-blocked-200 shadow-sm">
              {error}
            </div>
          )}

          <div className="flex gap-4 mb-8">
            <AudioRecorder onAudioReady={handleAudioReady} isTranscribing={isTranscribing} />
            <input ref={imageInput} type="file" accept="image/png,image/jpeg,image/webp" onChange={handleImage} className="hidden" />
            <button type="button" onClick={() => imageInput.current?.click()} className="btn-secondary w-full justify-center bg-white/50 hover:bg-white/80 border-gray-200/60 text-gray-700 shadow-sm transition-all duration-200 hover:shadow-md">
              <Upload className="w-5 h-5 mr-2 text-gray-500" />
              {imageName ? "Change Incident Image" : "Add Incident Image"}
            </button>
          </div>

          {imageUrl && (
            <div className="mb-6 rounded-2xl border border-gray-200/60 overflow-hidden bg-white/50 shadow-inner">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={imageUrl} alt="Selected incident" className="w-full max-h-56 object-cover" />
              <div className="flex items-center justify-between gap-3 p-4 text-sm bg-white/40 backdrop-blur-md">
                <span className="truncate font-medium text-gray-700">{imageName}</span>
                <button type="button" onClick={clearImage} className="text-blocked-600 font-bold hover:text-blocked-800 transition-colors shrink-0">Remove</button>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Describe what is happening..."
              className="w-full h-44 p-5 border border-gray-200/80 rounded-2xl text-lg mb-6 focus:outline-none focus:border-teal-400 focus:ring-4 focus:ring-teal-500/15 resize-none font-ml transition-all duration-300 bg-white/60 shadow-inner placeholder:text-gray-400 text-gray-800"
              disabled={isSubmitting || isTranscribing}
            />
            <button
              type="submit"
              className="w-full text-lg py-4 bg-teal-600 hover:bg-teal-700 text-white font-bold rounded-2xl flex items-center justify-center transition-all duration-300 shadow-lg shadow-teal-900/20 hover:shadow-xl hover:-translate-y-1 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-lg"
              disabled={(!text.trim() && !imageUrl) || isSubmitting || isTranscribing}
            >
              {isSubmitting ? "Analyzing Incident..." : (
                <>
                  ANALYZE INCIDENT
                  <Send className="w-5 h-5 ml-2" />
                </>
              )}
            </button>
          </form>

          <div className="mt-10 pt-8 border-t border-gray-200/60 text-center">
            <button onClick={handleDemo} className="btn-secondary text-sm bg-white/60 hover:bg-white shadow-sm border-gray-200/60 transition-all duration-200">
              <AudioLines className="w-4 h-4" />
              Try Guided Demo
            </button>
            <p className="text-xs text-gray-400 mt-4 font-medium tracking-wide">Uses seeded synthetic data. No real emergency dispatch.</p>
          </div>
        </div>

        <div className="w-full max-w-xl grid grid-cols-3 gap-5 mt-10 reveal reveal-delay-3">
          <div className="bg-white/70 backdrop-blur-xl rounded-2xl border border-white/60 p-5 text-center shadow-lg shadow-navy-900/5 transition-all duration-300 hover:shadow-xl hover:-translate-y-1"><CheckCircle2 className="w-7 h-7 mx-auto text-safe-600 mb-3 drop-shadow-sm" /><p className="metric-label text-safe-700 tracking-wider">SAFE</p></div>
          <div className="bg-white/70 backdrop-blur-xl rounded-2xl border border-white/60 p-5 text-center shadow-lg shadow-navy-900/5 transition-all duration-300 hover:shadow-xl hover:-translate-y-1"><CircleHelp className="w-7 h-7 mx-auto text-unknown-500 mb-3 drop-shadow-sm" /><p className="metric-label text-unknown-700 tracking-wider">UNKNOWN</p></div>
          <div className="bg-white/70 backdrop-blur-xl rounded-2xl border border-white/60 p-5 text-center shadow-lg shadow-navy-900/5 transition-all duration-300 hover:shadow-xl hover:-translate-y-1"><XCircle className="w-7 h-7 mx-auto text-blocked-500 mb-3 drop-shadow-sm" /><p className="metric-label text-blocked-700 tracking-wider">BLOCKED</p></div>
        </div>

      </div>
    </div>
  );
}
