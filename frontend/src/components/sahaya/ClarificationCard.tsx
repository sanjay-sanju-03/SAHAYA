"use client";

import { useState } from "react";
import { ClarificationQuestion } from "@/lib/api";

interface ClarificationCardProps {
  question: ClarificationQuestion;
  onAnswer: (answer: string) => Promise<void>;
}

export function ClarificationCard({ question, onAnswer }: ClarificationCardProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [freeText, setFreeText] = useState("");

  const handleSelect = async (ans: string) => {
    setIsSubmitting(true);
    try {
      await onAnswer(ans);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isFreeText = question.options.length === 1 && question.options[0].startsWith("(");

  return (
    <div className="card p-6 md:p-8 text-center max-w-xl mx-auto mt-8">
      <h2 className="text-2xl font-bold mb-2">{question.question}</h2>
      <p className="text-gray-500 font-ml text-lg mb-8">{question.question_ml}</p>

      {isFreeText ? (
        <div className="flex flex-col gap-4">
          <input
            type="text"
            className="w-full p-4 border rounded-xl text-lg focus:ring-2 focus:ring-navy-400 outline-none"
            placeholder={question.options[0]}
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
            disabled={isSubmitting}
          />
          <button
            onClick={() => handleSelect(freeText)}
            disabled={!freeText.trim() || isSubmitting}
            className="btn-primary"
          >
            {isSubmitting ? "Submitting..." : "Submit Answer"}
          </button>
        </div>
      ) : (
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          {question.options.map((opt) => (
            <button
              key={opt}
              onClick={() => handleSelect(opt)}
              disabled={isSubmitting}
              className="btn-secondary flex-1 py-4 text-lg font-bold"
            >
              {opt.replace("_", " ")}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
