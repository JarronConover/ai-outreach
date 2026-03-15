import { useEffect, useState, useCallback } from "react";
import { Mail, RefreshCw, ChevronDown, ChevronUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface InboxEmail {
  id: string;
  from_name: string;
  from_email: string;
  subject: string;
  body_snippet: string;
  category: string;
  status: string;
  received_at: string;
  person_name: string;
  people_id: string | null;
  note: string;
}

function categoryVariant(cat: string): "teal" | "green" | "gray" {
  const c = (cat || "").toLowerCase();
  if (c === "interested" || c === "demo_request") return "green";
  if (c === "manual") return "teal";
  return "gray";
}

function statusVariant(s: string): "teal" | "green" | "gray" {
  const v = (s || "").toLowerCase();
  if (v === "responded") return "green";
  if (v === "pending_response") return "teal";
  return "gray";
}

function formatDate(val: string | null | undefined): string {
  if (!val) return "—";
  try {
    return new Date(val).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return val;
  }
}

function categoryLabel(cat: string): string {
  const map: Record<string, string> = {
    interested: "Interested",
    not_interested: "Not Interested",
    demo_request: "Demo Request",
    manual: "Manual",
    other: "Other",
  };
  return map[cat?.toLowerCase()] ?? cat ?? "—";
}

export function EmailsPage() {
  const [emails, setEmails] = useState<InboxEmail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string>("all");

  const fetchEmails = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/emails");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setEmails(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load emails");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEmails();
  }, [fetchEmails]);

  const categories = ["all", "interested", "not_interested", "demo_request", "manual", "other"];

  const filtered =
    categoryFilter === "all"
      ? emails
      : emails.filter((e) => e.category?.toLowerCase() === categoryFilter);

  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#0d9488]/10">
            <Mail className="size-5 text-[#0d9488]" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-[#111827]">Inbox Emails</h1>
            {!loading && (
              <p className="text-sm text-[#9ca3af]">{emails.length} total</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchEmails}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-[#6b7280] hover:text-[#111827] hover:bg-[#f3f4f6] transition-colors"
          >
            <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Category filter */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {categories.map((c) => (
          <button
            key={c}
            onClick={() => setCategoryFilter(c)}
            className={`px-3 py-1 rounded-full text-xs font-medium capitalize transition-colors ${
              categoryFilter === c
                ? "bg-[#0d9488] text-white"
                : "bg-white/60 border border-[#e5e7eb] text-[#6b7280] hover:text-[#111827]"
            }`}
          >
            {c === "all" ? "All" : categoryLabel(c)}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 text-red-600 text-sm">
          {error}
        </div>
      )}

      <div className="panel overflow-hidden">
        {loading && emails.length === 0 ? (
          <div className="px-5 py-16 text-center text-sm text-[#9ca3af]">
            Loading emails…
          </div>
        ) : filtered.length === 0 ? (
          <div className="px-5 py-16 text-center text-sm text-[#9ca3af]">
            {categoryFilter !== "all"
              ? `No ${categoryLabel(categoryFilter)} emails.`
              : "No inbox emails yet. Run the inbox agent to scan Gmail."}
          </div>
        ) : (
          <div className="divide-y divide-white/40">
            {filtered.map((email, i) => {
              const expanded = expandedId === email.id;
              return (
                <div key={email.id || i} className="hover:bg-white/30 transition-colors">
                  <button
                    className="w-full text-left px-5 py-4"
                    onClick={() => setExpandedId(expanded ? null : email.id)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-[#111827] text-sm truncate">
                            {email.from_name || email.from_email || "Unknown"}
                          </span>
                          {email.person_name && (
                            <span className="text-xs text-[#9ca3af] shrink-0">
                              → {email.person_name}
                            </span>
                          )}
                        </div>
                        <p className="text-sm font-medium text-[#374151] truncate mb-0.5">
                          {email.subject || "(no subject)"}
                        </p>
                        {!expanded && (
                          <p className="text-xs text-[#9ca3af] truncate">
                            {email.body_snippet || ""}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Badge variant={categoryVariant(email.category)}>
                          {categoryLabel(email.category)}
                        </Badge>
                        <Badge variant={statusVariant(email.status)}>
                          {email.status || "new"}
                        </Badge>
                        <span className="text-xs text-[#9ca3af]">
                          {formatDate(email.received_at)}
                        </span>
                        {expanded ? (
                          <ChevronUp className="size-3.5 text-[#9ca3af]" />
                        ) : (
                          <ChevronDown className="size-3.5 text-[#9ca3af]" />
                        )}
                      </div>
                    </div>
                  </button>

                  {expanded && (
                    <div className="px-5 pb-4">
                      <div className="p-3 rounded-lg bg-[#f9fafb] border border-[#e5e7eb] text-xs text-[#374151] whitespace-pre-wrap font-mono leading-relaxed">
                        {email.body_snippet || "(no preview available)"}
                      </div>
                      {email.note && (
                        <p className="mt-2 text-xs text-[#6b7280] italic">
                          Note: {email.note}
                        </p>
                      )}
                      <div className="mt-2 flex gap-4 text-xs text-[#9ca3af]">
                        <span>From: {email.from_email}</span>
                        <span>Received: {formatDate(email.received_at)}</span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
