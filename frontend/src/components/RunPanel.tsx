import { useState, useEffect } from "react";
import { Loader2, CheckCircle2, XCircle, Play } from "lucide-react";
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

      {job && (
        <div className="rounded-lg border border-[#e5e7eb] bg-[#f9fafb] p-4 text-sm space-y-2">
          <div className="flex items-center gap-2 font-medium">
            {job.status === "pending" && (
              <>
                <Loader2 className="size-4 animate-spin text-[#9ca3af]" />
                <span className="text-[#4b5563]">Pending…</span>
              </>
            )}
            {job.status === "running" && (
              <>
                <Loader2 className="size-4 animate-spin text-[#0d9488]" />
                <span className="text-[#0d9488]">Running</span>
              </>
            )}
            {job.status === "completed" && (
              <>
                <CheckCircle2 className="size-4 text-green-600" />
                <span className="text-green-700">Completed</span>
              </>
            )}
            {job.status === "failed" && (
              <>
                <XCircle className="size-4 text-red-500" />
                <span className="text-red-600">Failed</span>
              </>
            )}
          </div>

          {job.status === "completed" && job.result && (
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mt-1">
              <dt className="text-[#9ca3af]">Found</dt>
              <dd className="font-medium text-[#111827]">{job.result.people_found ?? "—"}</dd>
              <dt className="text-[#9ca3af]">Written</dt>
              <dd className="font-medium text-[#111827]">{job.result.people_written ?? "—"}</dd>
              <dt className="text-[#9ca3af]">Duplicates skipped</dt>
              <dd className="font-medium text-[#111827]">{job.result.duplicates_skipped ?? "—"}</dd>
            </dl>
          )}

          {job.status === "failed" && job.error && (
            <p className="text-xs text-red-500 break-all">{job.error}</p>
          )}
        </div>
      )}
    </div>
  );
}
