import { useEffect, useState, useCallback } from "react";
import { Calendar, RefreshCw } from "lucide-react";
import { ConfirmDelete } from "@/components/ConfirmDelete";
import { Badge } from "@/components/ui/badge";

interface Demo {
  id: string;
  type: string;
  status: string;
  date: string;
  person_name: string;
  person_email: string;
  company_name: string;
  count: number;
  event_id: string;
}

function statusVariant(status: string): "teal" | "green" | "gray" {
  const s = (status || "").toLowerCase();
  if (s === "scheduled") return "teal";
  if (s === "completed") return "green";
  return "gray";
}

function formatDate(val: string | null | undefined): string {
  if (!val) return "—";
  try {
    return new Date(val).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return val;
  }
}

function typeLabel(t: string): string {
  const map: Record<string, string> = {
    discovery: "Discovery",
    tech: "Tech Demo",
    pricing: "Pricing",
    onboarding: "Onboarding",
  };
  return map[t?.toLowerCase()] ?? t ?? "—";
}

export function DemosPage() {
  const [demos, setDemos] = useState<Demo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "scheduled" | "completed" | "canceled">("all");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);

  const fetchDemos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/demos");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDemos(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load demos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDemos();
  }, [fetchDemos]);

  const handleDelete = async (id: string) => {
    if (deletingId) return;
    setDeletingId(id);
    try {
      const res = await fetch(`/api/demos/${id}`, { method: "DELETE" });
      if (res.ok || res.status === 204) {
        setDemos((prev) => prev.filter((d) => d.id !== id));
      }
    } finally {
      setDeletingId(null);
    }
  };

  const filtered =
    filter === "all" ? demos : demos.filter((d) => d.status?.toLowerCase() === filter);

  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#0d9488]/10">
            <Calendar className="size-5 text-[#0d9488]" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-[#111827]">Demos</h1>
            {!loading && (
              <p className="text-sm text-[#9ca3af]">{demos.length} total</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1 p-1 rounded-lg bg-[#f3f4f6]">
            {(["all", "scheduled", "completed", "canceled"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 rounded-md text-xs font-medium capitalize transition-colors ${
                  filter === f
                    ? "bg-white text-[#111827] shadow-sm"
                    : "text-[#6b7280] hover:text-[#111827]"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
          <button
            onClick={fetchDemos}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-[#6b7280] hover:text-[#111827] hover:bg-[#f3f4f6] transition-colors"
          >
            <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 text-red-600 text-sm">
          {error}
        </div>
      )}

      <div className="panel overflow-hidden">
        {loading && demos.length === 0 ? (
          <div className="px-5 py-16 text-center text-sm text-[#9ca3af]">Loading demos…</div>
        ) : filtered.length === 0 ? (
          <div className="px-5 py-16 text-center text-sm text-[#9ca3af]">
            {filter !== "all" ? `No ${filter} demos.` : "No demos scheduled yet."}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#e5e7eb] bg-white/30">
                  {["Type", "Contact", "Company", "Date & Time", "Status", "#", ""].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-medium text-[#9ca3af] uppercase tracking-wide whitespace-nowrap"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((d, i) => (
                  <tr
                    key={d.id || i}
                    className="border-b border-white/40 hover:bg-white/30 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-[#111827] whitespace-nowrap">
                      {typeLabel(d.type)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <p className="text-[#111827] font-medium">{d.person_name || "—"}</p>
                      {d.person_email && (
                        <p className="text-xs text-[#9ca3af]">{d.person_email}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-[#4b5563] whitespace-nowrap">
                      {d.company_name || "—"}
                    </td>
                    <td className="px-4 py-3 text-[#4b5563] whitespace-nowrap text-xs">
                      {formatDate(d.date)}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={statusVariant(d.status)}>
                        {d.status || "—"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-[#9ca3af] text-center">
                      {d.count ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      <ConfirmDelete
                        id={d.id}
                        pending={pendingId}
                        deleting={deletingId}
                        onRequest={setPendingId}
                        onConfirm={(id) => { setPendingId(null); handleDelete(id); }}
                        onCancel={() => setPendingId(null)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
