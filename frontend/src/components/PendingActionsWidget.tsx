import { useState, useEffect, useCallback } from "react";
import { Loader2, CheckCircle2, ClipboardList, Mail, Calendar, Check, CheckCheck, X, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useJob } from "@/hooks/useJob";

interface PendingAction {
  id: string;
  kind: "email" | "calendar";
  email_type?: string;
  recipient_email?: string;
  recipient_name?: string;
  subject?: string;
  body?: string;
  event_type?: string;
  event_title?: string;
  attendees?: string[];
  start_time?: string;
  status: "pending" | "confirming" | "confirmed" | "canceled";
  created_at: string;
}

const EMAIL_TYPE_LABELS: Record<string, string> = {
  prospect_outreach: "Intro Email",
  client_outreach: "Client Check-in",
  followup_email: "Follow-up",
  demo_invite: "Demo Invite",
  inbox_reply_interested: "Reply — Interested",
  inbox_reply_not_interested: "Reply — Not Interested",
  inbox_reply_demo_request: "Reply — Demo Request",
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

export function PendingActionsWidget({ onJobComplete }: Props) {
  const [actions, setActions] = useState<PendingAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [confirmingIds, setConfirmingIds] = useState<Set<string>>(new Set());
  const [cancelingIds, setCancelingIds] = useState<Set<string>>(new Set());
  const [isCancelingAll, setIsCancelingAll] = useState(false);
  const [bulkJobId, setBulkJobId] = useState<string | null>(null);
  const [isBulkConfirming, setIsBulkConfirming] = useState(false);

  const { job: bulkJob } = useJob(isBulkConfirming ? bulkJobId : null);

  const fetchPending = useCallback(async () => {
    try {
      const res = await fetch("/api/outreach/pending");
      if (!res.ok) return;
      const data: PendingAction[] = await res.json();
      setActions(data.filter((a) => a.status === "pending"));
    } catch {
      // ignore polling errors
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load + poll every 3s
  useEffect(() => {
    fetchPending();
    const id = setInterval(fetchPending, 15000);
    return () => clearInterval(id);
  }, [fetchPending]);

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

  async function handleConfirmOne(actionId: string) {
    setConfirmingIds((prev) => new Set(prev).add(actionId));
    setErrorMsg(null);
    try {
      const res = await fetch(`/api/outreach/pending/${actionId}/confirm`, { method: "POST" });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `HTTP ${res.status}`);
      }
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

  async function handleConfirmAll() {
    setIsBulkConfirming(true);
    setErrorMsg(null);
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

  async function handleCancelOne(actionId: string) {
    setCancelingIds((prev) => new Set(prev).add(actionId));
    setErrorMsg(null);
    try {
      const res = await fetch(`/api/outreach/pending/${actionId}`, { method: "DELETE" });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `HTTP ${res.status}`);
      }
      await fetchPending();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Cancel failed.");
    } finally {
      setCancelingIds((prev) => {
        const next = new Set(prev);
        next.delete(actionId);
        return next;
      });
    }
  }

  async function handleCancelAll() {
    setIsCancelingAll(true);
    setErrorMsg(null);
    try {
      const res = await fetch("/api/outreach/pending", { method: "DELETE" });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `HTTP ${res.status}`);
      }
      await fetchPending();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Cancel all failed.");
    } finally {
      setIsCancelingAll(false);
    }
  }

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

  return (
    <div className="panel overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-[#e5e7eb]">
        <h2 className="text-sm font-semibold text-[#111827] flex items-center gap-2">
          <ClipboardList className="size-4 text-[#0d9488]" />
          Pending Actions
          {actions.length > 0 && (
            <span className="ml-1 text-xs font-normal text-[#9ca3af]">
              {actions.length}
            </span>
          )}
        </h2>
      </div>

      {errorMsg && (
        <div className="px-5 pt-3 pb-1">
          <p className="text-xs text-red-500">{errorMsg}</p>
        </div>
      )}

      {loading && (
        <div className="px-5 py-8 flex justify-center">
          <Loader2 className="size-4 animate-spin text-[#9ca3af]" />
        </div>
      )}

      {!loading && actions.length === 0 && (
        <div className="px-5 py-6 flex flex-col items-center gap-2">
          <CheckCircle2 className="size-5 text-[#0d9488]" />
          <p className="text-xs text-[#9ca3af] text-center">No pending actions.</p>
        </div>
      )}

      {!loading && actions.length > 0 && (
        <>
          {/* Confirm All / Cancel All bar */}
          <div className="flex items-center justify-between px-5 py-3 border-b border-[#f3f4f6] bg-[#f9fafb]">
            <p className="text-xs text-[#6b7280]">
              {actions.length} action{actions.length !== 1 ? "s" : ""} awaiting approval
            </p>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs gap-1.5 text-red-500 border-red-200 hover:bg-red-50 hover:text-red-600"
                onClick={handleCancelAll}
                disabled={isCancelingAll || isBulkConfirming}
              >
                {isCancelingAll ? (
                  <Loader2 className="size-3 animate-spin" />
                ) : (
                  <XCircle className="size-3" />
                )}
                Cancel All
              </Button>
              <Button
                size="sm"
                className="h-7 text-xs gap-1.5"
                onClick={handleConfirmAll}
                disabled={isBulkConfirming || isCancelingAll}
              >
                {isBulkConfirming ? (
                  <Loader2 className="size-3 animate-spin" />
                ) : (
                  <CheckCheck className="size-3" />
                )}
                Confirm All
              </Button>
            </div>
          </div>

          {/* Action grid — 2 columns on wider screens */}
          <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
            {actions.map((action) => {
              const isConfirming = confirmingIds.has(action.id) || action.status === "confirming";
              return (
                <div
                  key={action.id}
                  className="flex items-start gap-3 rounded-lg border border-[#e5e7eb] bg-white px-4 py-3 hover:border-[#0d9488]/40 hover:bg-[#f0fdfa] transition-colors"
                >
                  <div className="mt-0.5 shrink-0 rounded-md bg-[#f0fdfa] p-1.5 text-[#0d9488]">
                    {action.kind === "email" ? (
                      <Mail className="size-3.5" />
                    ) : (
                      <Calendar className="size-3.5" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-1">
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
                        <p className="text-[11px] text-[#9ca3af] truncate italic mt-0.5">{action.subject}</p>
                        {action.body && (
                          <p className="text-[10px] text-[#9ca3af] truncate mt-0.5 border-t border-[#f3f4f6] pt-1">
                            {action.body.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 120)}
                          </p>
                        )}
                      </>
                    ) : (
                      <>
                        <p className="text-xs font-medium text-[#111827] truncate">
                          {action.event_title}
                        </p>
                        {action.start_time && (
                          <p className="text-[11px] text-[#6b7280] mt-0.5">{formatTime(action.start_time)}</p>
                        )}
                        {action.attendees && action.attendees.length > 0 && (
                          <p className="text-[11px] text-[#9ca3af] truncate mt-0.5">
                            {action.attendees.join(", ")}
                          </p>
                        )}
                      </>
                    )}
                  </div>
                  <div className="flex flex-col gap-1 shrink-0 self-center">
                    <button
                      onClick={() => handleConfirmOne(action.id)}
                      disabled={isConfirming || isBulkConfirming || cancelingIds.has(action.id) || isCancelingAll}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium bg-[#0d9488] text-white hover:bg-[#0f766e] disabled:opacity-50 transition-colors"
                      title="Confirm"
                    >
                      {isConfirming ? (
                        <Loader2 className="size-2.5 animate-spin" />
                      ) : (
                        <Check className="size-2.5" />
                      )}
                      Confirm
                    </button>
                    <button
                      onClick={() => handleCancelOne(action.id)}
                      disabled={cancelingIds.has(action.id) || isConfirming || isBulkConfirming || isCancelingAll}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium border border-red-200 text-red-500 hover:bg-red-50 hover:text-red-600 disabled:opacity-50 transition-colors"
                      title="Cancel"
                    >
                      {cancelingIds.has(action.id) ? (
                        <Loader2 className="size-2.5 animate-spin" />
                      ) : (
                        <X className="size-2.5" />
                      )}
                      Cancel
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
