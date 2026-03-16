import { useEffect, useState, useCallback } from "react";
import { Users, ExternalLink, RefreshCw } from "lucide-react";
import { ConfirmDelete } from "@/components/ConfirmDelete";
import { Badge } from "@/components/ui/badge";

interface Person {
  id: string;
  name: string;
  title: string;
  email: string;
  phone: string;
  linkedin: string;
  stage: string;
  company_name: string;
  last_contact: string;
  last_response: string;
  last_contact_date: string;
  last_response_date: string;
}

function stageBadgeVariant(stage: string): "teal" | "green" | "gray" {
  const s = (stage || "").toUpperCase();
  if (s === "PROSPECTING" || s === "PROSPECT") return "teal";
  if (s === "INTERESTED" || s === "CLIENT") return "green";
  return "gray";
}

function formatDate(val: string | null | undefined): string {
  if (!val) return "—";
  try {
    return new Date(val).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return val;
  }
}

export function PeoplePage() {
  const [people, setPeople] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);

  const fetchPeople = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/people");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setPeople(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load people");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPeople();
  }, [fetchPeople]);

  const handleDelete = async (id: string) => {
    if (deletingId) return;
    setDeletingId(id);
    try {
      const res = await fetch(`/api/people/${id}`, { method: "DELETE" });
      if (res.ok || res.status === 204) {
        setPeople((prev) => prev.filter((p) => p.id !== id));
      }
    } finally {
      setDeletingId(null);
    }
  };

  const filtered = people.filter((p) => {
    const q = search.toLowerCase();
    return (
      !q ||
      p.name?.toLowerCase().includes(q) ||
      p.email?.toLowerCase().includes(q) ||
      p.company_name?.toLowerCase().includes(q) ||
      p.title?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#0d9488]/10">
            <Users className="size-5 text-[#0d9488]" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-[#111827]">People</h1>
            {!loading && (
              <p className="text-sm text-[#9ca3af]">{people.length} contacts</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="text"
            placeholder="Search…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-[#e5e7eb] text-sm text-[#374151] placeholder:text-[#9ca3af] bg-white/70 focus:outline-none focus:ring-2 focus:ring-[#0d9488]/30"
          />
          <button
            onClick={fetchPeople}
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
        {loading && people.length === 0 ? (
          <div className="px-5 py-16 text-center text-sm text-[#9ca3af]">Loading people…</div>
        ) : filtered.length === 0 ? (
          <div className="px-5 py-16 text-center text-sm text-[#9ca3af]">
            {search ? "No results match your search." : "No contacts yet."}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#e5e7eb] bg-white/30">
                  {[
                    "Name", "Title", "Company", "Email", "LinkedIn",
                    "Stage", "Last Contact", "Last Response", "",
                  ].map((h) => (
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
                {filtered.map((p, i) => (
                  <tr
                    key={p.id || i}
                    className="border-b border-white/40 hover:bg-white/30 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-[#111827] whitespace-nowrap">
                      {p.name || "—"}
                    </td>
                    <td className="px-4 py-3 text-[#4b5563] whitespace-nowrap">
                      {p.title || "—"}
                    </td>
                    <td className="px-4 py-3 text-[#4b5563] whitespace-nowrap">
                      {p.company_name || "—"}
                    </td>
                    <td className="px-4 py-3">
                      {p.email ? (
                        <a href={`mailto:${p.email}`} className="text-[#0d9488] hover:underline">
                          {p.email}
                        </a>
                      ) : (
                        <span className="text-[#9ca3af]">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {p.linkedin ? (
                        <a
                          href={p.linkedin}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[#0d9488] hover:underline"
                        >
                          <ExternalLink className="size-3" />
                          Profile
                        </a>
                      ) : (
                        <span className="text-[#9ca3af]">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={stageBadgeVariant(p.stage)}>
                        {p.stage || "prospect"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-[#4b5563] whitespace-nowrap text-xs">
                      {formatDate(p.last_contact_date || p.last_contact)}
                    </td>
                    <td className="px-4 py-3 text-[#4b5563] whitespace-nowrap text-xs">
                      {formatDate(p.last_response_date || p.last_response)}
                    </td>
                    <td className="px-4 py-3">
                      <ConfirmDelete
                        id={p.id}
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
