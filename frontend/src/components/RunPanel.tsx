import { useState, useEffect } from "react";
import { Loader2, XCircle, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useJob } from "@/hooks/useJob";

interface RunPanelProps {
  onJobComplete: () => void;
}

export function RunPanel({ onJobComplete }: RunPanelProps) {
  const [jobId, setJobId] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const { job, isPolling } = useJob(jobId);

  useEffect(() => {
    if (job?.status === "completed" && !isPolling) {
      onJobComplete();
    }
  }, [job?.status, isPolling, onJobComplete]);

  async function handleRun() {
    setIsStarting(true);
    try {
      const res = await fetch("/api/run", { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setJobId(data.job_id);
    } catch (err) {
      console.error("Failed to start job", err);
    } finally {
      setIsStarting(false);
    }
  }

  const isRunning = isPolling || isStarting;

  return (
    <div className="panel p-6 flex flex-col gap-5">
      <div>
        <h2 className="text-sm font-semibold text-[#111827] mb-1">Prospecting Agent</h2>
        <p className="text-xs text-[#9ca3af]">
          Generates leads based on your ICP and writes them to Google Sheets.
        </p>
      </div>

      <Button
        size="lg"
        className="w-full gap-2 cursor-pointer"
        onClick={handleRun}
        disabled={isRunning}
      >
        {isRunning ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <Play className="size-4" />
        )}
        {isStarting ? "Starting…" : isPolling ? "Running…" : "Run Agent"}
      </Button>

      {job?.status === "failed" && (
        <div className="rounded-lg border border-red-200/60 bg-red-50/40 p-4 text-sm">
          <div className="flex items-center gap-2 font-medium mb-1">
            <XCircle className="size-4 text-red-500" />
            <span className="text-red-600">Failed</span>
          </div>
          {job.error && <p className="text-xs text-red-500 break-all">{job.error}</p>}
        </div>
      )}
    </div>
  );
}
