import { useState } from "react";
import { Building2, Globe, RefreshCw, ArrowRight } from "lucide-react";
import { ConfirmDelete } from "@/components/ConfirmDelete";

interface Company {
  id: string;
  name: string;
  industry: string;
  employee_count: string | number;
  website: string;
  city: string;
  state: string;
  phone: string;
}

interface CompaniesWidgetProps {
  companies: Company[];
  loading: boolean;
  onRefresh: () => void;
  onSeeMore?: () => void;
}

export function CompaniesWidget({ companies: allCompanies, loading, onRefresh, onSeeMore }: CompaniesWidgetProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [removed, setRemoved] = useState<Set<string>>(new Set());

  const visible = allCompanies.filter((c) => !removed.has(c.id));
  const displayed = visible.slice(0, 10);
  const total = visible.length;

  const handleDelete = async (id: string) => {
    if (deletingId) return;
    setDeletingId(id);
    try {
      const res = await fetch(`/api/companies/${id}`, { method: "DELETE" });
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
          <span className="inline-flex items-center gap-2">
            <Building2 className="size-4 text-[#0d9488]" />
            Companies
          </span>
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
          No companies yet. Run the prospect agent to generate leads.
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#e5e7eb] bg-white/30">
                  {["Company", "Industry", "Employees", "Location", "Website", ""].map((h) => (
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
                {displayed.map((c, i) => (
                  <tr
                    key={c.id || i}
                    className="border-b border-white/40 hover:bg-white/30 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-[#111827] whitespace-nowrap">
                      {c.name || "—"}
                    </td>
                    <td className="px-4 py-3 text-[#4b5563]">{c.industry || "—"}</td>
                    <td className="px-4 py-3 text-[#4b5563] text-center">{c.employee_count || "—"}</td>
                    <td className="px-4 py-3 text-[#4b5563] whitespace-nowrap">
                      {[c.city, c.state].filter(Boolean).join(", ") || "—"}
                    </td>
                    <td className="px-4 py-3">
                      {c.website ? (
                        <a
                          href={c.website.startsWith("http") ? c.website : `https://${c.website}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[#0d9488] hover:underline"
                        >
                          <Globe className="size-3" />
                          {c.website.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                        </a>
                      ) : (
                        <span className="text-[#9ca3af]">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <ConfirmDelete
                        id={c.id}
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
                See all {total} companies
                <ArrowRight className="size-3.5" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
