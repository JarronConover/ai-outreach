import { useState, useRef } from "react";
import { Upload, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

type TableKey = "companies" | "people" | "demos";

const TABLES: { key: TableKey; label: string; hint: string }[] = [
  { key: "companies", label: "Companies", hint: "Import companies first" },
  { key: "people",    label: "People",    hint: "Requires companies imported" },
  { key: "demos",     label: "Demos",     hint: "Requires people imported" },
];

interface ImportResult {
  table: string;
  imported: number;
  errors: string[];
}

export function CsvImportWidget() {
  const [activeTab, setActiveTab] = useState<TableKey>("companies");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    setFileName(f?.name ?? null);
    setResult(null);
  }

  function handleTabChange(tab: TableKey) {
    setActiveTab(tab);
    setResult(null);
    setFileName(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  async function handleUpload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setLoading(true);
    setResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`/api/import/${activeTab}`, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`);
      setResult(data as ImportResult);
    } catch (err) {
      setResult({ table: activeTab, imported: 0, errors: [err instanceof Error ? err.message : "Upload failed"] });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel overflow-hidden">
      <div className="px-5 py-4 border-b border-[#e5e7eb]">
        <h2 className="text-sm font-semibold text-[#111827] flex items-center gap-2">
          <Upload className="size-4 text-[#0d9488]" />
          Import from CSV
        </h2>
        <p className="text-[11px] text-[#9ca3af] mt-0.5">
          Export each tab from Google Sheets as CSV, then upload here. Import order: Companies → People → Demos.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#e5e7eb]">
        {TABLES.map((t) => (
          <button
            key={t.key}
            onClick={() => handleTabChange(t.key)}
            className={`flex-1 px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === t.key
                ? "text-[#0d9488] border-b-2 border-[#0d9488] bg-[#f0fdfa]"
                : "text-[#6b7280] hover:text-[#111827]"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="p-4 flex flex-col gap-3">
        <p className="text-[11px] text-[#9ca3af]">
          {TABLES.find((t) => t.key === activeTab)?.hint}
        </p>

        {/* File input */}
        <label className="flex flex-col items-center gap-2 cursor-pointer rounded-lg border-2 border-dashed border-[#e5e7eb] px-4 py-5 hover:border-[#0d9488]/50 hover:bg-[#f0fdfa] transition-colors">
          <Upload className="size-5 text-[#9ca3af]" />
          <span className="text-xs text-[#6b7280]">
            {fileName ? fileName : "Click to select a CSV file"}
          </span>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={handleFileChange}
          />
        </label>

        <Button
          size="sm"
          className="w-full gap-1.5"
          onClick={handleUpload}
          disabled={!fileName || loading}
        >
          {loading ? (
            <Loader2 className="size-3 animate-spin" />
          ) : (
            <Upload className="size-3" />
          )}
          {loading ? "Importing…" : `Import ${TABLES.find((t) => t.key === activeTab)?.label}`}
        </Button>

        {/* Result */}
        {result && (
          <div className="rounded-lg border border-[#e5e7eb] p-3 flex flex-col gap-1.5">
            <div className="flex items-center gap-1.5">
              {result.imported > 0 ? (
                <CheckCircle2 className="size-3.5 text-[#0d9488] shrink-0" />
              ) : (
                <AlertCircle className="size-3.5 text-amber-500 shrink-0" />
              )}
              <span className="text-xs font-medium text-[#111827]">
                {result.imported} row{result.imported !== 1 ? "s" : ""} imported
              </span>
            </div>
            {result.errors.length > 0 && (
              <ul className="text-[10px] text-[#9ca3af] space-y-0.5 max-h-24 overflow-y-auto">
                {result.errors.map((e, i) => (
                  <li key={i} className="text-amber-600">{e}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
