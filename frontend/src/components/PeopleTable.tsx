import { useState } from "react";
import { ExternalLink, RefreshCw, ArrowRight } from "lucide-react";
import { ConfirmDelete } from "@/components/ConfirmDelete";
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

const STAGE_PRIORITY: Record<string, number> = {
  client: 7,
  onboarding: 6,
  pricing: 5,
  demo_completed: 4,
  demo_scheduled: 3,
  contacted: 2,
  prospect: 1,
};

function stagePriority(stage: string): number {
  return STAGE_PRIORITY[(stage || "").toLowerCase()] ?? 0;
}

function stageBadgeVariant(stage: string): "teal" | "green" | "gray" {
  const s = (stage || "").toLowerCase();
  if (s === "prospect" || s === "prospecting") return "teal";
  if (s === "client" || s === "onboarding") return "green";
  return "gray";
}

interface PeopleTableProps {
  people: Record<string, string>[];
  loading: boolean;
  onRefresh: () => void;
  onSeeMore?: () => void;
}

export function PeopleTable({ people: rawPeople, loading, onRefresh, onSeeMore }: PeopleTableProps) {
  const allPeople = rawPeople as unknown as Person[];
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [removed, setRemoved] = useState<Set<string>>(new Set());

  const visible = allPeople.filter((p) => !removed.has(p.id));
  const displayed = visible
    .slice()
    .sort((a, b) => stagePriority(b.stage) - stagePriority(a.stage))
    .slice(0, 10);
  const total = visible.length;

  const handleDelete = async (id: string) => {
    if (deletingId) return;
    setDeletingId(id);
    try {
      const res = await fetch(`/api/people/${id}`, { method: "DELETE" });
      if (res.ok || res.status === 204) {
        setRemoved((prev) => new Set(prev).add(id));
      }
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="panel overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/40">
        <h2 className="text-sm font-semibold text-[#111827]">
          Contacts
          {total > 0 && (
            <span className="ml-2 text-xs font-normal text-[#9ca3af]">
              {total} total
            </span>
          )}
        </h2>
        <button
          onClick={onRefresh}
          className="p-1.5 rounded-md text-[#9ca3af] hover:text-[#111827] hover:bg-[#f3f4f6] transition-colors"
          title="Refresh"
        >
          <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {loading && total === 0 ? (
        <div className="px-5 py-12 text-center text-sm text-[#9ca3af]">Loading…</div>
      ) : total === 0 ? (
        <div className="px-5 py-12 text-center text-sm text-[#9ca3af]">
          No contacts yet. Run the agent to generate leads.
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#e5e7eb] bg-white/30">
                  {["Name", "Title", "Company", "LinkedIn", "Email", "Stage", ""].map((h) => (
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
                {displayed.map((p, i) => (
                  <tr
                    key={p.id || i}
                    className="border-b border-white/40 hover:bg-white/30 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-[#111827] whitespace-nowrap">
                      {p.name || "—"}
                    </td>
                    <td className="px-4 py-3 text-[#4b5563] whitespace-nowrap">{p.title || "—"}</td>
                    <td className="px-4 py-3 text-[#4b5563] whitespace-nowrap">{p.company_name || "—"}</td>
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
                    <td className="px-4 py-3 text-[#4b5563]">
                      {p.email ? (
                        <a href={`mailto:${p.email}`} className="text-[#0d9488] hover:underline">
                          {p.email}
                        </a>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={stageBadgeVariant(p.stage)}>
                        {p.stage || "prospect"}
                      </Badge>
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
          {total > 10 && onSeeMore && (
            <div className="px-5 py-3 border-t border-white/40">
              <button
                onClick={onSeeMore}
                className="flex items-center gap-1.5 text-xs font-medium text-[#0d9488] hover:text-[#0f766e] transition-colors"
              >
                See all {total} contacts
                <ArrowRight className="size-3.5" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
