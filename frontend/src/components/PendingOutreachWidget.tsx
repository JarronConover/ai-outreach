import { useState, useEffect, useCallback } from "react";
import { Loader2, CheckCircle2, Zap, Mail, Calendar, Check, X, CheckCheck, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useJob } from "@/hooks/useJob";

interface PendingAction {
  id: string;
  kind: "email" | "calendar";
  // email fields
  email_type?: string;
  recipient_email?: string;
  recipient_name?: string;
  subject?: string;
  // calendar fields
  event_type?: string;
  event_title?: string;
  attendees?: string[];
  start_time?: string;
  // shared
  status: "pending" | "confirming" | "confirmed" | "canceling";
  created_at: string;
}

const EMAIL_TYPE_LABELS: Record<string, string> = {
  prospect_outreach: "Intro Email",
  client_outreach: "Client Check-in",
  followup_email: "Follow-up",
  demo_invite: "Demo Invite",
};

const EVENT_TYPE_LABELS: Record<string, string> = {
  demo_discovery: "Discovery Call",
  demo_tech: "Tech Demo",
  demo_pricing: "Pricing Call",
  demo_onboarding: "Onboarding",
  demo_client: "Client Review",
};

function formatTime(iso: string | undefined): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("en-US", {
      weekday: "short", month: "short", day: "numeric",
      hour: "numeric", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

interface Props {
  onJobComplete: () => void;
}

type State = "idle" | "planning" | "empty" | "loaded" | "error";

export function PendingOutreachWidget({ onJobComplete }: Props) {
  const [state, setState] = useState<State>("idle");
  const [planJobId, setPlanJobId] = useState<string | null>(null);
  const [actions, setActions] = useState<PendingAction[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  // Track per-action confirm job ids to show spinners
  const [confirmingIds, setConfirmingIds] = useState<Set<string>>(new Set());
  // Track bulk confirm job
  const [bulkJobId, setBulkJobId] = useState<string | null>(null);
  const [isBulkConfirming, setIsBulkConfirming] = useState(false);

  const { job: planJob } = useJob(state === "planning" ? planJobId : null);
  const { job: bulkJob } = useJob(isBulkConfirming ? bulkJobId : null);

  // Load pending actions from server
  const fetchPending = useCallback(async () => {
    try {
      const res = await fetch("/api/outreach/pending");
      if (!res.ok) return;
      const data: PendingAction[] = await res.json();
      setActions(data);
      if (state === "loaded" || state === "empty") {
        setState(data.length > 0 ? "loaded" : "empty");
      }
    } catch {
      // ignore polling errors
    }
  }, [state]);

  // Poll pending actions every 3s when in loaded/empty state
  useEffect(() => {
    if (state !== "loaded" && state !== "empty") return;
    const id = setInterval(fetchPending, 3000);
    return () => clearInterval(id);
  }, [state, fetchPending]);

  // React to plan job completing
  useEffect(() => {
    if (state !== "planning" || !planJob) return;
    if (planJob.status === "completed") {
      fetch("/api/outreach/pending")
        .then((r) => r.json())
        .then((data: PendingAction[]) => {
          setActions(data);
          setState(data.filter((a) => a.status === "pending").length > 0 ? "loaded" : "empty");
        })
        .catch(() => setState("empty"));
    } else if (planJob.status === "failed") {
      setErrorMsg(planJob.error || "Planning failed.");
      setState("error");
    }
  }, [planJob?.status, state]);

  // React to bulk confirm job completing
  useEffect(() => {
    if (!isBulkConfirming || !bulkJob) return;
    if (bulkJob.status === "completed") {
      setIsBulkConfirming(false);
      setBulkJobId(null);
      fetchPending();
      onJobComplete();
    } else if (bulkJob.status === "failed") {
      setIsBulkConfirming(false);
      setBulkJobId(null);
      setErrorMsg(bulkJob.error || "Confirm all failed.");
      fetchPending();
    }
  }, [bulkJob?.status, isBulkConfirming]);

  async function handleGeneratePlan() {
    setErrorMsg(null);
    setActions([]);
    setState("planning");
    try {
      const res = await fetch("/api/outreach/plan", { method: "POST" });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `HTTP ${res.status}`);
      }
      const { job_id } = await res.json();
      setPlanJobId(job_id);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to start plan.");
      setState("error");
    }
  }

  async function handleConfirmOne(actionId: string) {
    setConfirmingIds((prev) => new Set(prev).add(actionId));
    try {
      const res = await fetch(`/api/outreach/pending/${actionId}/confirm`, { method: "POST" });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `HTTP ${res.status}`);
      }
      // Poll until the job completes then refresh
      const { job_id } = await res.json();
      await pollUntilDone(job_id);
      await fetchPending();
      onJobComplete();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Confirm failed.");
    } finally {
      setConfirmingIds((prev) => {
        const next = new Set(prev);
        next.delete(actionId);
        return next;
      });
    }
  }

  async function handleCancelOne(actionId: string) {
    try {
      await fetch(`/api/outreach/pending/${actionId}`, { method: "DELETE" });
      await fetchPending();
    } catch {
      // ignore
    }
  }

  async function handleConfirmAll() {
    setIsBulkConfirming(true);
    try {
      const res = await fetch("/api/outreach/pending/confirm-all", { method: "POST" });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `HTTP ${res.status}`);
      }
      const { job_id } = await res.json();
      if (job_id) {
        setBulkJobId(job_id);
      } else {
        setIsBulkConfirming(false);
        await fetchPending();
      }
    } catch (err) {
      setIsBulkConfirming(false);
      setErrorMsg(err instanceof Error ? err.message : "Confirm all failed.");
    }
  }

  async function handleCancelAll() {
    try {
      await fetch("/api/outreach/pending", { method: "DELETE" });
      setActions([]);
      setState("empty");
    } catch {
      // ignore
    }
  }

  // Simple polling helper for individual confirm jobs
  async function pollUntilDone(jobId: string, maxMs = 30000): Promise<void> {
    const start = Date.now();
    while (Date.now() - start < maxMs) {
      await new Promise((r) => setTimeout(r, 1500));
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        if (!res.ok) break;
        const job = await res.json();
        if (job.status === "completed" || job.status === "failed") return;
      } catch {
        break;
      }
    }
  }

  const pendingActions = actions.filter((a) => a.status === "pending");
  const confirmedCount = actions.filter((a) => a.status === "confirmed").length;
  const hasPending = pendingActions.length > 0;

  return (
    <div className="panel overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-[#e5e7eb]">
        <h2 className="text-sm font-semibold text-[#111827] flex items-center gap-2">
          <Zap className="size-4 text-[#0d9488]" />
          Pending Outreach
          {hasPending && (
            <span className="ml-1 text-xs font-normal text-[#9ca3af]">
              {pendingActions.length} pending
            </span>
          )}
        </h2>
        {(state === "loaded" || state === "empty") && (
          <button
            onClick={handleGeneratePlan}
            className="text-xs text-[#0d9488] hover:underline"
            title="Re-generate plan"
          >
            Refresh plan
          </button>
        )}
      </div>

      {/* Error */}
      {state === "error" && (
        <div className="px-5 py-4">
          <p className="text-xs text-red-500 mb-3">{errorMsg}</p>
          <Button size="sm" variant="outline" onClick={() => setState("idle")}>
            Try again
          </Button>
        </div>
      )}

      {/* Idle */}
      {state === "idle" && (
        <div className="px-5 py-6 flex flex-col items-center gap-3">
          <p className="text-xs text-[#9ca3af] text-center">
            Generate a plan to preview outreach actions before sending.
          </p>
          <Button size="sm" onClick={handleGeneratePlan} className="w-full">
            <Zap className="size-3.5 mr-1.5" />
            Generate Outreach Plan
          </Button>
        </div>
      )}

      {/* Planning */}
      {state === "planning" && (
        <div className="px-5 py-8 flex flex-col items-center gap-2 text-[#9ca3af]">
          <Loader2 className="size-5 animate-spin text-[#0d9488]" />
          <p className="text-xs">Analysing CRM and planning actions…</p>
        </div>
      )}

      {/* Empty — plan ran but nothing to do */}
      {state === "empty" && (
        <div className="px-5 py-6 flex flex-col items-center gap-3">
          <CheckCircle2 className="size-5 text-[#0d9488]" />
          <p className="text-xs text-[#9ca3af] text-center">
            Nothing to send right now. All contacts are up to date.
          </p>
          <Button size="sm" variant="outline" onClick={handleGeneratePlan} className="w-full">
            Refresh plan
          </Button>
        </div>
      )}

      {/* Loaded — show pending actions */}
      {state === "loaded" && (
        <>
          {/* Bulk action bar */}
          <div className="flex items-center gap-2 px-5 py-2.5 border-b border-[#f3f4f6] bg-[#f9fafb]">
            <Button
              size="sm"
              className="h-7 text-xs gap-1.5 flex-1"
              onClick={handleConfirmAll}
              disabled={isBulkConfirming || !hasPending}
            >
              {isBulkConfirming ? (
                <Loader2 className="size-3 animate-spin" />
              ) : (
                <CheckCheck className="size-3" />
              )}
              Confirm All
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs gap-1.5 flex-1"
              onClick={handleCancelAll}
              disabled={isBulkConfirming || !hasPending}
            >
              <XCircle className="size-3" />
              Cancel All
            </Button>
          </div>

          {/* Action list */}
          <div className="divide-y divide-[#f3f4f6] max-h-[480px] overflow-y-auto">
            {pendingActions.map((action) => {
              const isConfirming = confirmingIds.has(action.id) || action.status === "confirming";
              return (
                <div key={action.id} className="px-4 py-3 hover:bg-[#f9fafb] transition-colors">
                  <div className="flex items-start gap-2">
                    <div className="mt-0.5 shrink-0 text-[#0d9488]">
                      {action.kind === "email" ? (
                        <Mail className="size-3.5" />
                      ) : (
                        <Calendar className="size-3.5" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <Badge variant="teal" className="text-[10px] px-1.5 py-0">
                          {action.kind === "email"
                            ? (EMAIL_TYPE_LABELS[action.email_type || ""] ?? action.email_type)
                            : (EVENT_TYPE_LABELS[action.event_type || ""] ?? action.event_type)}
                        </Badge>
                      </div>
                      {action.kind === "email" ? (
                        <>
                          <p className="text-xs font-medium text-[#111827] truncate">
                            {action.recipient_name}
                          </p>
                          <p className="text-[11px] text-[#6b7280] truncate">{action.recipient_email}</p>
                          <p className="text-[11px] text-[#9ca3af] truncate italic">{action.subject}</p>
                        </>
                      ) : (
                        <>
                          <p className="text-xs font-medium text-[#111827] truncate">
                            {action.event_title}
                          </p>
                          {action.start_time && (
                            <p className="text-[11px] text-[#6b7280]">{formatTime(action.start_time)}</p>
                          )}
                          {action.attendees && action.attendees.length > 0 && (
                            <p className="text-[11px] text-[#9ca3af] truncate">
                              {action.attendees.join(", ")}
                            </p>
                          )}
                        </>
                      )}
                    </div>
                    <div className="flex flex-col gap-1 shrink-0">
                      <button
                        onClick={() => handleConfirmOne(action.id)}
                        disabled={isConfirming}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-[#0d9488] text-white hover:bg-[#0f766e] disabled:opacity-50 transition-colors"
                        title="Confirm"
                      >
                        {isConfirming ? (
                          <Loader2 className="size-2.5 animate-spin" />
                        ) : (
                          <Check className="size-2.5" />
                        )}
                        Send
                      </button>
                      <button
                        onClick={() => handleCancelOne(action.id)}
                        disabled={isConfirming}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium text-[#6b7280] hover:bg-[#f3f4f6] disabled:opacity-50 transition-colors"
                        title="Cancel"
                      >
                        <X className="size-2.5" />
                        Skip
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
            {confirmedCount > 0 && pendingActions.length === 0 && (
              <div className="px-5 py-4 text-center text-xs text-[#9ca3af]">
                <CheckCircle2 className="size-4 text-[#0d9488] mx-auto mb-1" />
                All actions confirmed.
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
