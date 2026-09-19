"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getMissingInfo, answerClarification, ClarificationQuestion } from "@/lib/api";
import { ClarificationCard } from "@/components/sahaya/ClarificationCard";
import { Loader2 } from "lucide-react";

export default function ClarifyPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();
  const [question, setQuestion] = useState<ClarificationQuestion | null>(null);
  const [loading, setLoading] = useState(true);
  const [caseNotFound, setCaseNotFound] = useState(false);

  const fetchQuestion = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getMissingInfo(id);
      if (res.complete) {
        router.push(`/incident/${id}`);
      } else {
        setQuestion(res.question);
      }
    } catch (err) {
      if (err instanceof Error && err.message.startsWith("API 404:")) {
        setCaseNotFound(true);
      } else {
        console.error(err);
      }
    } finally {
      setLoading(false);
    }
  }, [id, router]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchQuestion();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [fetchQuestion]);

  const handleAnswer = async (answer: string) => {
    if (!question) return;
    await answerClarification(id, question.key, answer);
    // Fetch next question
    await fetchQuestion();
  };

  if (loading) {
    return <div className="p-10 text-center"><Loader2 className="w-8 h-8 animate-spin mx-auto text-navy-600"/></div>;
  }

  if (caseNotFound) {
    return (
      <div className="page-container flex items-center justify-center min-h-[60vh]">
        <div className="card p-8 w-full max-w-lg text-center">
          <h1 className="text-2xl font-bold mb-3">This case is no longer available</h1>
          <p className="text-gray-600 mb-6">
            The backend was restarted, so this temporary case was removed. Create a new case or open the demo scenario.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link href="/" className="btn-primary">Create New Case</Link>
            <Link href="/incident/demo-001/clarify" className="btn-secondary">Try Demo Scenario</Link>
          </div>
        </div>
      </div>
    );
  }

  if (!question) return null;

  return (
    <div className="page-container min-h-[calc(100vh-64px)] flex flex-col justify-center pb-20">
      <div className="text-center mb-4 text-gray-500 font-semibold tracking-wider uppercase text-sm">
        Clarification Required
      </div>
      <ClarificationCard question={question} onAnswer={handleAnswer} />
    </div>
  );
}
