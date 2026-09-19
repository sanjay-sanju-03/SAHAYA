import { AuditLog } from "@/lib/api";
import { format } from "date-fns";
import { Bot, User, Settings } from "lucide-react";

interface AuditTimelineProps {
  logs: AuditLog[];
}

export function AuditTimeline({ logs }: AuditTimelineProps) {
  // Sort logs oldest first
  const sorted = [...logs].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );

  return (
    <div className="card p-6 mt-8">
      <h2 className="text-xl font-bold mb-6">Case Audit Log</h2>
      <div className="ml-2">
        {sorted.map((log) => (
          <div key={log.id} className="timeline-item">
            <div className={`timeline-dot timeline-dot-${log.actor_type}`}>
              {log.actor_type === "ai" && <Bot className="w-3 h-3 text-navy-600" />}
              {log.actor_type === "system" && <Settings className="w-3 h-3 text-gray-500" />}
              {log.actor_type === "human" && <User className="w-3 h-3 text-safe-600" />}
            </div>
            <div className="pt-1">
              <div className="flex items-baseline gap-2">
                <span className="font-semibold text-gray-900">{log.action.replaceAll("_", " ").toUpperCase()}</span>
                <span className="text-xs text-gray-500 font-mono">
                  {format(new Date(log.created_at), "dd MMM yyyy · HH:mm")}
                </span>
              </div>
              <p className="text-sm text-gray-600 mt-1 whitespace-pre-line">{log.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
