"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { getIncident } from "@/lib/api";
import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";

function ProcessingScreen() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const id = searchParams.get("id");

  const [step, setStep] = useState(0);
  const [caseNotFound, setCaseNotFound] = useState(false);

  useEffect(() => {
    if (!id) {
      router.push("/");
      return;
    }

    let isMounted = true;

    // Simulated progress steps for better UX (spec §7 Screen 2)
    const timers = [
      setTimeout(() => isMounted && setStep(1), 800),
      setTimeout(() => isMounted && setStep(2), 2000),
    ];

    // Poll backend until status changes from 'analyzing'
    const poll = setInterval(async () => {
      try {
        const incident = await getIncident(id);
        if (incident.status !== "analyzing") {
          clearInterval(poll);
          if (isMounted) {
            setStep(3);
            setTimeout(() => {
              router.push(`/incident/${id}`);
            }, 500);
          }
        }
      } catch (err) {
        if (err instanceof Error && err.message.startsWith("API 404:")) {
          clearInterval(poll);
          if (isMounted) setCaseNotFound(true);
        } else {
          console.error("Poll failed", err);
        }
      }
    }, 1500);

    return () => {
      isMounted = false;
      timers.forEach(clearTimeout);
      clearInterval(poll);
    };
  }, [id, router]);

  const steps = [
    "Reading report",
    "Extracting requirements",
    "Checking missing information",
  ];

  if (caseNotFound) {
    return (
      <div className="page-container flex items-center justify-center min-h-[60vh]">
        <div className="card p-8 w-full max-w-lg text-center">
          <AlertTriangle className="w-10 h-10 text-unknown-600 mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-3">This case is no longer available</h1>
          <p className="text-gray-600 mb-6">
            The backend restarted while this case was being processed. Create a new case or use the demo scenario.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link href="/" className="btn-primary">Create New Case</Link>
            <Link href="/incident/demo-001/review" className="btn-secondary">Try Demo Scenario</Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container flex items-center justify-center min-h-[60vh]">
      <div className="card p-8 w-full max-w-md">
        <p className="metric-label text-center mb-2">UNDERSTANDING INCIDENT</p>
        <h2 className="text-2xl font-bold mb-6 text-center">Preparing a safe assessment</h2>

        <div className="space-y-4">
          {steps.map((label, idx) => {
            const isDone = step > idx;
            const isActive = step === idx;

            return (
              <div
                key={label}
                className={`progress-step ${isDone ? 'progress-step-done bg-safe-50' : isActive ? 'progress-step-active bg-navy-50' : 'progress-step-pending'}`}
              >
                <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center">
                  {isDone ? (
                    <CheckCircle2 className="w-5 h-5 text-safe-600" />
                  ) : isActive ? (
                    <Loader2 className="w-5 h-5 text-navy-600 animate-spin" />
                  ) : (
                    <div className="w-2 h-2 rounded-full bg-gray-300" />
                  )}
                </div>
                <span className="text-lg">{label}</span>
              </div>
            );
          })}
        </div>
        <p className="text-sm text-gray-500 text-center mt-6">AI understands. Rules verify. Humans decide.</p>
      </div>
    </div>
  );
}

export default function ProcessingPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center"><Loader2 className="w-8 h-8 animate-spin mx-auto text-navy-600"/></div>}>
      <ProcessingScreen />
    </Suspense>
  );
}
