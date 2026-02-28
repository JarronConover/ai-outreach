import { useState, useEffect, useRef } from "react";

export interface Job {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
  type?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  result?: {
    people_found?: number;
    people_written?: number;
    duplicates_skipped?: number;
    [key: string]: unknown;
  };
  error?: string;
}

export function useJob(jobId: string | null) {
  const [job, setJob] = useState<Job | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      setIsPolling(false);
      return;
    }

    setIsPolling(true);

    const poll = async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        if (!res.ok) return;
        const data: Job = await res.json();
        setJob(data);
        if (data.status === "completed" || data.status === "failed") {
          setIsPolling(false);
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        }
      } catch {
        // network error — keep polling
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 2000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [jobId]);

  return { job, isPolling };
}
