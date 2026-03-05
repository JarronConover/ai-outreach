import { useState, useEffect, useCallback } from "react";
import { Loader2, CheckCircle2, Inbox, UserCheck, UserX, Check } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface InboxEmail {
  id: string;
  message_id: string;
  from_email: string;
  from_name?: string;
  people_id?: string;
  subject: string;
  body_snippet: string;
  received_at?: string;
  category: string;
  status: string;
  note?: string;
}

function formatRelativeTime(iso: string | undefined): string {
  if (!iso) return "";
  try {
    const date = new Date(iso);
    const diff = Date.now() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  } catch {
    return "";
  }
}

export function NeedsResponseWidget() {
  const [emails, setEmails] = useState<InboxEmail[]>([]);
  const [loading, setLoading] = useState(true);
  const [resolvingIds, setResolvingIds] = useState<Set<string>>(new Set());
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchEmails = useCallback(async () => {
    try {
      const res = await fetch("/api/inbox/needs-response");
      if (!res.ok) return;
      const data: InboxEmail[] = await res.json();
      setEmails(data);
    } catch {
      // ignore polling errors
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load + poll every 30s
  useEffect(() => {
    fetchEmails();
    const id = setInterval(fetchEmails, 30000);
    return () => clearInterval(id);
  }, [fetchEmails]);

  async function handleResolve(emailId: string) {
    setResolvingIds((prev) => new Set(prev).add(emailId));
    setErrorMsg(null);
    try {
      const res = await fetch(`/api/inbox/emails/${emailId}/resolve`, { method: "POST" });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `HTTP ${res.status}`);
      }
      setEmails((prev) => prev.filter((e) => e.id !== emailId));
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to resolve email.");
    } finally {
      setResolvingIds((prev) => {
        const next = new Set(prev);
        next.delete(emailId);
        return next;
      });
    }
  }

  return (
    <div className="panel overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-[#e5e7eb]">
        <h2 className="text-sm font-semibold text-[#111827] flex items-center gap-2">
          <Inbox className="size-4 text-[#0d9488]" />
          Needs Response
          {emails.length > 0 && (
            <span className="ml-1 text-xs font-normal text-[#9ca3af]">
              {emails.length}
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

      {!loading && emails.length === 0 && (
        <div className="px-5 py-6 flex flex-col items-center gap-2">
          <CheckCircle2 className="size-5 text-[#0d9488]" />
          <p className="text-xs text-[#9ca3af] text-center">No emails need a manual response.</p>
        </div>
      )}

      {!loading && emails.length > 0 && (
        <div className="divide-y divide-[#f3f4f6]">
          {emails.map((email) => {
            const isResolving = resolvingIds.has(email.id);
            const inCRM = Boolean(email.people_id);
            const displayName = email.from_name || email.from_email;

            return (
              <div
                key={email.id}
                className="flex items-start gap-3 px-5 py-4 hover:bg-[#f9fafb] transition-colors"
              >
                {/* Avatar / icon */}
                <div className="mt-0.5 shrink-0 rounded-full bg-[#f3f4f6] p-2 text-[#6b7280]">
                  <Inbox className="size-3.5" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <p className="text-xs font-medium text-[#111827] truncate">{displayName}</p>
                    {inCRM ? (
                      <Badge variant="teal" className="text-[10px] px-1.5 py-0 gap-0.5 shrink-0">
                        <UserCheck className="size-2.5" />
                        In CRM
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-[10px] px-1.5 py-0 gap-0.5 shrink-0 text-[#9ca3af] border-[#e5e7eb]">
                        <UserX className="size-2.5" />
                        Unknown
                      </Badge>
                    )}
                    {email.received_at && (
                      <span className="text-[10px] text-[#9ca3af] shrink-0 ml-auto">
                        {formatRelativeTime(email.received_at)}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-[#374151] truncate font-medium">{email.subject || "(no subject)"}</p>
                  {email.body_snippet && (
                    <p className="text-[11px] text-[#9ca3af] truncate mt-0.5 italic">
                      {email.body_snippet.slice(0, 120)}
                    </p>
                  )}
                  {email.note && (
                    <p className="text-[10px] text-[#6b7280] mt-1 border-t border-[#f3f4f6] pt-1 line-clamp-2">
                      {email.note}
                    </p>
                  )}
                  <p className="text-[10px] text-[#9ca3af] mt-0.5">{email.from_email}</p>
                </div>

                {/* Action */}
                <div className="shrink-0 self-center">
                  <button
                    onClick={() => handleResolve(email.id)}
                    disabled={isResolving}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium border border-[#d1d5db] text-[#374151] hover:bg-[#f3f4f6] disabled:opacity-50 transition-colors"
                    title="Mark resolved"
                  >
                    {isResolving ? (
                      <Loader2 className="size-2.5 animate-spin" />
                    ) : (
                      <Check className="size-2.5" />
                    )}
                    Resolved
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
