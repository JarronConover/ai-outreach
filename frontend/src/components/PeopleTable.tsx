import { useEffect, useState, useCallback } from "react";
import { ExternalLink, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface Person {
  id: string;
  name: string;
  company_id: string;
  email: string;
  phone: string;
  linkedin: string;
  title: string;
  stage: string;
  last_demo_id: string;
  next_demo_id: string;
  last_response: string;
  last_contact: string;
  last_response_date: string;
  last_contact_date: string;
  company_name: string;
}

function stageBadgeVariant(stage: string): "teal" | "green" | "gray" {
  const s = (stage || "").toUpperCase();
  if (s === "PROSPECTING") return "teal";
  if (s === "INTERESTED") return "green";
  return "gray";
}

interface PeopleTableProps {
  refreshKey: number;
}

export function PeopleTable({ refreshKey }: PeopleTableProps) {
  const [people, setPeople] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPeople = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/people");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Person[] = await res.json();
      setPeople(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load people");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPeople();
  }, [fetchPeople, refreshKey]);

  return (
    <div className="panel overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/40">
        <h2 className="text-sm font-semibold text-[#111827]">
          Contacts
          {people.length > 0 && (
            <span className="ml-2 text-xs font-normal text-[#9ca3af]">
              {people.length} total
            </span>
          )}
        </h2>
        <button
          onClick={fetchPeople}
          className="p-1.5 rounded-md text-[#9ca3af] hover:text-[#111827] hover:bg-[#f3f4f6] transition-colors"
          title="Refresh"
        >
          <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {loading && people.length === 0 ? (
        <div className="px-5 py-12 text-center text-sm text-[#9ca3af]">Loading…</div>
      ) : error ? (
        <div className="px-5 py-12 text-center text-sm text-red-500">{error}</div>
      ) : people.length === 0 ? (
        <div className="px-5 py-12 text-center text-sm text-[#9ca3af]">
          No contacts yet. Run the agent to generate leads.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#e5e7eb] bg-white/30">
                {["Name", "Title", "Company", "Email", "LinkedIn", "Stage"].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-xs font-medium text-[#9ca3af] uppercase tracking-wide"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {people.map((p, i) => (
                <tr
                  key={p.id || i}
                  className="border-b border-white/40 hover:bg-white/30 transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-[#111827] whitespace-nowrap">
                    {p.name || "—"}
                  </td>
                  <td className="px-4 py-3 text-[#4b5563] whitespace-nowrap">{p.title || "—"}</td>
                  <td className="px-4 py-3 text-[#4b5563] whitespace-nowrap">{p.company_name || "—"}</td>
                  <td className="px-4 py-3 text-[#4b5563]">
                    {p.email ? (
                      <a
                        href={`mailto:${p.email}`}
                        className="text-[#0d9488] hover:underline"
                      >
                        {p.email}
                      </a>
                    ) : (
                      "—"
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
                      {p.stage || "PROSPECTING"}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
