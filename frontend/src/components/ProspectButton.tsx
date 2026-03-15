import { useState, useEffect, useCallback } from "react";
import { Play, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { useJob } from "@/hooks/useJob";

interface ProspectButtonProps {
  onComplete: () => void;
  collapsed?: boolean;
}

export function ProspectButton({ onComplete, collapsed = false }: ProspectButtonProps) {
  const [jobId, setJobId] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const { job, isPolling } = useJob(jobId);

  useEffect(() => {
    if (job?.status === "completed") {
      onComplete();
      const t = setTimeout(() => setJobId(null), 4000);
      return () => clearTimeout(t);
    }
    if (job?.status === "failed") {
      const t = setTimeout(() => setJobId(null), 5000);
      return () => clearTimeout(t);
    }
  }, [job?.status, onComplete]);

  const handleRun = useCallback(async () => {
    if (starting || isPolling) return;
    setStarting(true);
    try {
      const res = await fetch("/api/prospect", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setJobId(data.job_id);
      }
    } catch {
      // ignore
    } finally {
      setStarting(false);
    }
  }, [starting, isPolling]);

  const isRunning = starting || isPolling;
  const isDone = job?.status === "completed";
  const isFailed = job?.status === "failed";

  const statusLabel = starting ? "Starting…" : isPolling ? "Running…" : isDone ? "Done" : isFailed ? "Failed" : "Idle";

  const iconBtn = (
    <button
      onClick={handleRun}
      disabled={isRunning}
      title="Run Prospecting Agent"
      aria-label="Run prospecting agent"
      className={`flex items-center justify-center w-8 h-8 rounded-full transition-colors ${
        isRunning ? "bg-[#f3f4f6] cursor-not-allowed"
        : isDone ? "bg-emerald-50 cursor-default"
        : isFailed ? "bg-red-50 cursor-default"
        : "bg-[#0d9488] hover:bg-[#0f766e] cursor-pointer"
      }`}
    >
      {isRunning ? <Loader2 className="size-3.5 text-[#0d9488] animate-spin" />
        : isDone ? <CheckCircle2 className="size-3.5 text-emerald-600" />
        : isFailed ? <XCircle className="size-3.5 text-red-500" />
        : <Play className="size-3 text-white fill-white" />}
    </button>
  );

  if (collapsed) {
    return (
      <div className="flex justify-center py-1" title="Prospect">
        {iconBtn}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-white/60 border border-white/50 shadow-sm">
      <div className="flex items-center gap-2.5">
        <Play className="size-4 text-[#6b7280]" />
        <div>
          <p className="text-xs font-semibold text-[#111827]">Prospect</p>
          <p className={`text-[10px] ${isFailed ? "text-red-400" : isDone ? "text-[#0d9488]" : "text-[#9ca3af]"}`}>
            {statusLabel}
          </p>
        </div>
      </div>
      {iconBtn}
    </div>
  );
}
