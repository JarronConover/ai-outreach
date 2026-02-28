import { useState, useEffect } from "react";
import { Loader2, CheckCircle2, Zap, Mail, Calendar, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useJob } from "@/hooks/useJob";

interface PlannedEmail {
  recipient_email: string;
  recipient_name: string;
  subject: string;
  email_type: string;
}

interface PlannedEvent {
  event_title: string;
  attendees: string[];
  start_time: string | null;
  end_time: string | null;
  event_type: string;
}

interface PlanResult {
  emails: PlannedEmail[];
  calendar_events: PlannedEvent[];
  total_emails: number;
  total_events: number;
}

interface RunResult {
  emails_sent: number;
  calendar_events_created: number;
  clients_contacted: number;
  prospects_contacted: number;
  demos_scheduled: number;
  followups_sent: number;
  errors: number;
  error_details: string[];
}

interface OutreachPanelProps {
  onJobComplete: () => void;
}

const EMAIL_TYPE_LABELS: Record<string, string> = {
  client_outreach: "Client Check-in",
  prospect_outreach: "New Prospect",
  followup_email: "Follow-up",
  demo_invite: "Demo Invite",
};

const EVENT_TYPE_LABELS: Record<string, string> = {
  demo_discovery: "Discovery",
  demo_tech: "Tech Demo",
  demo_pricing: "Pricing Demo",
  demo_onboarding: "Onboarding",
  demo_client: "Client Review",
};

function formatEventTime(isoString: string | null): string {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    return d.toLocaleString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

type PanelState = "idle" | "planning" | "reviewing" | "running" | "done" | "error";

export function OutreachPanel({ onJobComplete }: OutreachPanelProps) {
  const [state, setState] = useState<PanelState>("idle");
  const [planJobId, setPlanJobId] = useState<string | null>(null);
  const [runJobId, setRunJobId] = useState<string | null>(null);
  const [planResult, setPlanResult] = useState<PlanResult | null>(null);
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { job: planJob } = useJob(state === "planning" ? planJobId : null);
  const { job: runJob } = useJob(state === "running" ? runJobId : null);

  // React to plan job completing
  useEffect(() => {
    if (state !== "planning" || !planJob) return;
    if (planJob.status === "completed" && planJob.result) {
      setPlanResult(planJob.result as unknown as PlanResult);
      setState("reviewing");
    } else if (planJob.status === "failed") {
      setErrorMsg(planJob.error || "Planning failed.");
      setState("error");
    }
  }, [planJob?.status, state]);

  // React to run job completing
  useEffect(() => {
    if (state !== "running" || !runJob) return;
    if (runJob.status === "completed" && runJob.result) {
      setRunResult(runJob.result as unknown as RunResult);
      setState("done");
      onJobComplete();
    } else if (runJob.status === "failed") {
      setErrorMsg(runJob.error || "Outreach run failed.");
      setState("error");
    }
  }, [runJob?.status, state]);

  async function handlePlan() {
    setErrorMsg(null);
    setPlanResult(null);
    setRunResult(null);
    setState("planning");
    try {
      const res = await fetch("/api/outreach/plan", { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setPlanJobId(data.job_id);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to start plan.");
      setState("error");
    }
  }

  async function handleConfirm() {
    setState("running");
    try {
      const res = await fetch("/api/outreach/run", { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRunJobId(data.job_id);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to start run.");
      setState("error");
    }
  }

  function handleCancel() {
    setState("idle");
    setPlanResult(null);
    setPlanJobId(null);
  }

  function handleReset() {
    setState("idle");
    setPlanResult(null);
    setRunResult(null);
    setPlanJobId(null);
    setRunJobId(null);
    setErrorMsg(null);
  }

  const nothingToDo =
    state === "reviewing" && planResult && planResult.total_emails === 0 && planResult.total_events === 0;

  return (
    <div className="panel p-6 flex flex-col gap-5">
      <div>
        <h2 className="text-sm font-semibold text-[#111827] mb-1">Outreach Agent</h2>
        <p className="text-xs text-[#9ca3af]">
          Emails clients, prospects & demos based on your CRM.
        </p>
      </div>

      {/* ── Controls ── */}
      {(state === "idle" || state === "done" || state === "error") && (
        <Button
          size="lg"
          className="w-full gap-2 cursor-pointer"
          onClick={state === "done" || state === "error" ? handleReset : handlePlan}
        >
          <Zap className="size-4" />
          {state === "done" || state === "error" ? "Run Again" : "Plan Outreach"}
        </Button>
      )}

      {state === "planning" && (
        <Button size="lg" className="w-full gap-2" disabled>
          <Loader2 className="size-4 animate-spin" />
          Planning…
        </Button>
      )}

      {state === "running" && (
        <Button size="lg" className="w-full gap-2" disabled>
          <Loader2 className="size-4 animate-spin" />
          Sending…
        </Button>
      )}

      {/* ── Error state ── */}
      {state === "error" && errorMsg && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-600 break-all">
          {errorMsg}
        </div>
      )}

      {/* ── Nothing to do ── */}
      {nothingToDo && (
        <div className="rounded-lg border border-[#e5e7eb] bg-[#f9fafb] p-4 text-sm text-[#4b5563] text-center">
          Nothing to send based on current CRM data.
          <button
            onClick={handleCancel}
            className="mt-2 block mx-auto text-xs text-[#0d9488] hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ── Review section ── */}
      {state === "reviewing" && planResult && !nothingToDo && (
        <div className="flex flex-col gap-3">
          {/* Emails */}
          {planResult.emails.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-[#111827] mb-2">
                <Mail className="size-3.5 text-[#0d9488]" />
                Emails ({planResult.emails.length})
              </div>
              <div className="flex flex-col gap-2">
                {planResult.emails.map((e, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-[#e5e7eb] bg-[#f9fafb] px-3 py-2 text-xs"
                  >
                    <div className="text-[#9ca3af] mb-0.5">
                      {EMAIL_TYPE_LABELS[e.email_type] ?? e.email_type}
                    </div>
                    <div className="font-medium text-[#111827] truncate">{e.recipient_name}</div>
                    <div className="text-[#4b5563] truncate">{e.recipient_email}</div>
                    <div className="text-[#9ca3af] truncate mt-0.5 italic">{e.subject}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Calendar events */}
          {planResult.calendar_events.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-[#111827] mb-2">
                <Calendar className="size-3.5 text-[#0d9488]" />
                Calendar Events ({planResult.calendar_events.length})
              </div>
              <div className="flex flex-col gap-2">
                {planResult.calendar_events.map((c, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-[#e5e7eb] bg-[#f9fafb] px-3 py-2 text-xs"
                  >
                    <div className="text-[#9ca3af] mb-0.5">
                      {EVENT_TYPE_LABELS[c.event_type] ?? c.event_type}
                    </div>
                    <div className="font-medium text-[#111827] truncate">{c.event_title}</div>
                    <div className="text-[#4b5563]">{formatEventTime(c.start_time)}</div>
                    <div className="text-[#9ca3af] truncate mt-0.5">
                      {c.attendees.join(", ")}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Confirm / Cancel */}
          <div className="flex gap-2 pt-1">
            <Button
              className="flex-1 gap-1.5 cursor-pointer"
              onClick={handleConfirm}
            >
              <Send className="size-3.5" />
              Confirm & Send
            </Button>
            <Button
              variant="outline"
              className="flex-1 cursor-pointer"
              onClick={handleCancel}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* ── Done summary ── */}
      {state === "done" && runResult && (
        <div className="rounded-lg border border-[#e5e7eb] bg-[#f9fafb] p-4 text-sm space-y-2">
          <div className="flex items-center gap-2 font-medium">
            <CheckCircle2 className="size-4 text-green-600" />
            <span className="text-green-700">Completed</span>
          </div>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mt-1">
            <dt className="text-[#9ca3af]">Emails sent</dt>
            <dd className="font-medium text-[#111827]">{runResult.emails_sent}</dd>
            <dt className="text-[#9ca3af]">Calendar events</dt>
            <dd className="font-medium text-[#111827]">{runResult.calendar_events_created}</dd>
            {runResult.errors > 0 && (
              <>
                <dt className="text-red-400">Errors</dt>
                <dd className="font-medium text-red-500">{runResult.errors}</dd>
              </>
            )}
          </dl>
          {runResult.error_details?.length > 0 && (
            <div className="text-xs text-red-500 space-y-1 pt-1">
              {runResult.error_details.map((e, i) => (
                <p key={i} className="break-all">{e}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
