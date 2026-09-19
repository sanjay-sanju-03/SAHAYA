import { Check, HelpCircle, X } from "lucide-react";
import { EvaluationCheck } from "@/lib/api";

interface ConstraintCardProps {
  check: EvaluationCheck;
}

export function ConstraintCard({ check }: ConstraintCardProps) {
  const isSafe = check.status === "SAFE";
  const isUnknown = check.status === "UNKNOWN";

  const bgClass = isSafe
    ? "check-row-safe"
    : isUnknown
    ? "check-row-unknown"
    : "check-row-blocked";

  const iconClass = isSafe
    ? "check-icon-safe"
    : isUnknown
    ? "check-icon-unknown"
    : "check-icon-blocked";

  return (
    <div className={`check-row ${bgClass}`}>
      <div className={`check-icon ${iconClass}`}>
        {isSafe && <Check className="w-3 h-3" strokeWidth={3} />}
        {isUnknown && <HelpCircle className="w-3 h-3" strokeWidth={3} />}
        {!isSafe && !isUnknown && <X className="w-3 h-3" strokeWidth={3} />}
      </div>
      <div className="flex-1">
        <div className="text-sm font-semibold mb-1">
          {check.requirement_label}
        </div>
        <div className="text-xs text-gray-700 mb-2 font-medium">
          {check.resource_label}
        </div>
        <p className="text-sm text-gray-800">
          {check.reason}
        </p>
      </div>
    </div>
  );
}
