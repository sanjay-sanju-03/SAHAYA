import { CheckCircle2, HelpCircle, MinusCircle, XCircle } from "lucide-react";
import { EvaluationStatus } from "@/lib/api";

interface StatusBadgeProps {
  status: EvaluationStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  if (status === "SAFE") {
    return (
      <span className="badge badge-safe status-pulse">
        <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
        SAFE
      </span>
    );
  }
  if (status === "UNKNOWN") {
    return (
      <span className="badge badge-unknown">
        <HelpCircle className="w-4 h-4" aria-hidden="true" />
        UNKNOWN
      </span>
    );
  }
  if (status === "NOT_APPLICABLE") {
    return (
      <span className="badge badge-not-applicable">
        <MinusCircle className="w-4 h-4" aria-hidden="true" />
        NOT APPLICABLE
      </span>
    );
  }
  return (
    <span className="badge badge-blocked">
      <XCircle className="w-4 h-4" aria-hidden="true" />
      BLOCKED
    </span>
  );
}
