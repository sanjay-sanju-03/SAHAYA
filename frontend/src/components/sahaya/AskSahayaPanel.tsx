"use client";

import { useState } from "react";
import { Loader2, MessageCircle, Send, X } from "lucide-react";
import { AssistantAnswer, queryAssistant } from "@/lib/api";

const prompts = [
  "Why is this resource SAFE?",
  "What evidence supports this decision?",
  "How much accessible capacity remains?",
  "When was this resource verified?",
  "Did anything change after the evaluation?",
  "Why is the route BLOCKED while the resource is SAFE?",
];

export function AskSahayaPanel({ incidentId, resourceId }: { incidentId: string; resourceId: string }) {
  const [open, setOpen] = useState(false);
  const [language, setLanguage] = useState<"en" | "ml">("en");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AssistantAnswer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const ask = async (nextQuestion = question) => {
    if (!nextQuestion.trim()) return;
    setLoading(true);
    setError("");
    try {
      setAnswer(await queryAssistant(incidentId, resourceId, nextQuestion, language));
    } catch {
      setError("SAHAYA could not load the current evidence. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return <>
    <button type="button" onClick={() => setOpen(true)} className="btn-secondary"><MessageCircle className="h-4 w-4" />ASK SAHAYA</button>
    {open && <div className="fixed inset-0 z-50 flex items-end justify-center bg-navy-950/35 p-4 sm:items-center" role="dialog" aria-modal="true" aria-label="Ask SAHAYA">
      <section className="w-full max-w-xl rounded-2xl bg-white p-5 shadow-2xl sm:p-6">
        <div className="flex items-start justify-between gap-4"><div><p className="metric-label">READ-ONLY EVIDENCE ASSISTANT</p><h2 className="mt-1 text-xl font-bold text-navy-950">Ask SAHAYA</h2><p className="mt-1 text-sm text-gray-600">Answers use the current case, resource, route, and audit evidence only.</p></div><button type="button" aria-label="Close assistant" onClick={() => setOpen(false)} className="rounded-lg p-2 text-gray-500 hover:bg-gray-100"><X className="h-5 w-5" /></button></div>
        <div className="mt-4 flex gap-2"><button type="button" onClick={() => setLanguage("en")} className={"rounded-md px-3 py-1.5 text-xs font-bold " + (language === "en" ? "bg-teal-700 text-white" : "bg-gray-100 text-gray-600")}>English</button><button type="button" onClick={() => setLanguage("ml")} className={"rounded-md px-3 py-1.5 text-xs font-bold " + (language === "ml" ? "bg-teal-700 text-white" : "bg-gray-100 text-gray-600")}>മലയാളം</button></div>
        <div className="mt-4 flex flex-wrap gap-2">{prompts.map((prompt) => <button key={prompt} type="button" onClick={() => { setQuestion(prompt); ask(prompt); }} className="rounded-full border border-navy-100 px-3 py-2 text-left text-xs font-medium text-navy-700 hover:border-teal-500 hover:bg-teal-50">{prompt}</button>)}</div>
        <div className="mt-5 flex gap-2"><input value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") ask(); }} placeholder="Ask about this evidence…" className="min-w-0 flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm" /><button type="button" onClick={() => ask()} disabled={loading || !question.trim()} className="btn-primary px-3" aria-label="Ask question">{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}</button></div>
        {error && <p className="mt-3 text-sm text-blocked-700">{error}</p>}
        {answer && <div className="mt-5 rounded-xl border border-teal-100 bg-teal-50/50 p-4"><p className="whitespace-pre-wrap text-sm leading-6 text-navy-900">{answer.answer}</p><div className="mt-4 border-t border-teal-100 pt-3 text-xs text-gray-600"><p className="font-bold uppercase tracking-wide text-teal-800">Evidence</p><p className="mt-1">Requirement v{answer.evidence.requirement_version} · Resource v{answer.evidence.resource_version}{answer.evidence.route_version !== null ? " · Route v" + answer.evidence.route_version : ""}</p><p>Resource: {answer.evidence.resource_evaluation_status || "Not evaluated"} · Route: {answer.evidence.route_evaluation_status || "Not evaluated"}</p></div></div>}
        <p className="mt-4 text-xs text-gray-500">SAHAYA explains evidence. A coordinator makes all decisions.</p>
      </section>
    </div>}
  </>;
}
