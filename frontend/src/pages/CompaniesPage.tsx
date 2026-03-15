import { useEffect, useState, useCallback } from "react";
import { Building2, Globe, RefreshCw } from "lucide-react";

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

export function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCompanies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/companies");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setCompanies(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load companies");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCompanies();
  }, [fetchCompanies]);

  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#0d9488]/10">
            <Building2 className="size-5 text-[#0d9488]" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-[#111827]">Companies</h1>
            {!loading && (
              <p className="text-sm text-[#9ca3af]">{companies.length} total</p>
            )}
          </div>
        </div>
        <button
          onClick={fetchCompanies}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-[#6b7280] hover:text-[#111827] hover:bg-[#f3f4f6] transition-colors"
        >
          <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 text-red-600 text-sm">
          {error}
        </div>
      )}

      <div className="panel overflow-hidden">
        {loading && companies.length === 0 ? (
          <div className="px-5 py-16 text-center text-sm text-[#9ca3af]">
            Loading companies…
          </div>
        ) : companies.length === 0 ? (
          <div className="px-5 py-16 text-center text-sm text-[#9ca3af]">
            No companies yet. Run the prospect agent to generate leads.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#e5e7eb] bg-white/30">
                  {["Company", "Industry", "Employees", "Location", "Website", "Phone"].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-left text-xs font-medium text-[#9ca3af] uppercase tracking-wide"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {companies.map((c, i) => (
                  <tr
                    key={c.id || i}
                    className="border-b border-white/40 hover:bg-white/30 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-[#111827] whitespace-nowrap">
                      {c.name || "—"}
                    </td>
                    <td className="px-4 py-3 text-[#4b5563]">{c.industry || "—"}</td>
                    <td className="px-4 py-3 text-[#4b5563] text-center">
                      {c.employee_count || "—"}
                    </td>
                    <td className="px-4 py-3 text-[#4b5563] whitespace-nowrap">
                      {[c.city, c.state].filter(Boolean).join(", ") || "—"}
                    </td>
                    <td className="px-4 py-3">
                      {c.website ? (
                        <a
                          href={
                            c.website.startsWith("http") ? c.website : `https://${c.website}`
                          }
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
                    <td className="px-4 py-3 text-[#4b5563]">{c.phone || "—"}</td>
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
