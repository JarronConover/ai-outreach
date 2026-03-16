import { useEffect, useState, useCallback } from "react";
import { Cpu, Loader2 } from "lucide-react";

type OrchestratorStatus = "idle" | "pending" | "running";

interface OrchestratorSwitchProps {
  collapsed?: boolean;
  onStatusChange?: (status: OrchestratorStatus) => void;
}

export function OrchestratorSwitch({ collapsed = false, onStatusChange }: OrchestratorSwitchProps) {
  const [status, setStatus] = useState<OrchestratorStatus>("idle");
  const [loading, setLoading] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/orchestrator/status");
      if (!res.ok) return;
      const data = await res.json();
      const s: OrchestratorStatus = data.status === "idle" ? "idle" : data.status;
      setStatus(s);
      onStatusChange?.(s);
    } catch {
      // backend offline — keep current state
    }
  }, [onStatusChange]);

  useEffect(() => {
    fetchStatus();
    const id = setInterval(fetchStatus, 3000);
    return () => clearInterval(id);
  }, [fetchStatus]);

  const isActive = status === "pending" || status === "running";

  const handleToggle = async () => {
    if (loading) return;
    setLoading(true);
    try {
      if (isActive) {
        const res = await fetch("/api/orchestrator/stop", { method: "POST" });
        if (res.ok) setStatus("idle");
      } else {
        const res = await fetch("/api/orchestrator/start", { method: "POST" });
        if (res.ok) {
          const data = await res.json();
          setStatus(data.status === "already_running" ? "running" : "pending");
        }
      }
    } finally {
      setLoading(false);
      fetchStatus();
    }
  };

  const toggle = (
    <button
      onClick={handleToggle}
      disabled={loading}
      aria-label={isActive ? "Stop orchestrator" : "Start orchestrator"}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-200 focus:outline-none ${
        isActive ? "bg-[#0d9488]" : "bg-[#d1d5db]"
      } ${loading ? "opacity-60" : ""}`}
    >
      <span className={`inline-flex size-5 items-center justify-center rounded-full bg-white shadow-sm transition-transform duration-200 ${
        isActive ? "translate-x-5" : "translate-x-0.5"
      }`}>
        {(loading || status === "pending") && (
          <Loader2 className="size-3 text-[#0d9488] animate-spin" />
        )}
      </span>
    </button>
  );

  if (collapsed) {
    return (
      <div className="flex justify-center py-1" title="Orchestrator">
        {toggle}
      </div>
    );
  }

  const statusLabel = status === "running" ? "Running" : status === "pending" ? "Starting…" : "Idle";

  return (
    <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-white/60 border border-white/50 shadow-sm">
      <div className="flex items-center gap-2.5">
        <Cpu className="size-4 text-[#6b7280]" />
        <div>
          <p className="text-xs font-semibold text-[#111827]">Orchestrator</p>
          <p className="text-[10px] text-[#9ca3af]">{statusLabel}</p>
        </div>
      </div>
      {toggle}
    </div>
  );
}
