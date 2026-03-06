import { useState, useRef } from "react";
import { Upload, CheckCircle2, AlertCircle, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SmartImportResult {
  rows_read: number;
  companies_upserted: number;
  people_upserted: number;
  errors: string[];
}

export function CsvImportWidget() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SmartImportResult | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  function setFile(file: File | undefined) {
    if (!file) return;
    setFileName(file.name);
    setResult(null);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFile(e.target.files?.[0]);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    setFile(file);
    if (fileRef.current && file) {
      const dt = new DataTransfer();
      dt.items.add(file);
      fileRef.current.files = dt.files;
    }
  }

  async function handleUpload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setLoading(true);
    setResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/api/import/smart", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`);
      setResult(data as SmartImportResult);
    } catch (err) {
      setResult({
        rows_read: 0,
        companies_upserted: 0,
        people_upserted: 0,
        errors: [err instanceof Error ? err.message : "Upload failed"],
      });
    } finally {
      setLoading(false);
    }
  }

  const succeeded = result && (result.companies_upserted > 0 || result.people_upserted > 0);

  return (
    <div className="panel overflow-hidden">
      <div className="px-5 py-4 border-b border-[#e5e7eb]">
        <h2 className="text-sm font-semibold text-[#111827] flex items-center gap-2">
          <Sparkles className="size-4 text-[#0d9488]" />
          Import from CSV
        </h2>
        <p className="text-[11px] text-[#9ca3af] mt-0.5">
          Upload any CSV — columns are auto-detected and mapped to companies &amp; people.
        </p>
      </div>

      <div className="p-4 flex flex-col gap-3">
        {/* Drop zone */}
        <label
          className={`flex flex-col items-center gap-2 cursor-pointer rounded-lg border-2 border-dashed px-4 py-6 transition-colors ${
            dragOver
              ? "border-[#0d9488] bg-[#f0fdfa]"
              : "border-[#e5e7eb] hover:border-[#0d9488]/50 hover:bg-[#f0fdfa]"
          }`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <Upload className="size-5 text-[#9ca3af]" />
          <span className="text-xs text-[#6b7280] text-center">
            {fileName ? (
              <span className="text-[#0d9488] font-medium">{fileName}</span>
            ) : (
              <>Drop a CSV here or <span className="text-[#0d9488]">click to browse</span></>
            )}
          </span>
          <span className="text-[10px] text-[#9ca3af]">Any structure — contacts, leads, exports</span>
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
            <>
              <Loader2 className="size-3 animate-spin" />
              Analysing &amp; importing…
            </>
          ) : (
            <>
              <Sparkles className="size-3" />
              Import CSV
            </>
          )}
        </Button>

        {loading && (
          <p className="text-[10px] text-[#9ca3af] text-center">
            AI is mapping your columns — this may take a few seconds.
          </p>
        )}

        {/* Result */}
        {result && (
          <div className="rounded-lg border border-[#e5e7eb] p-3 flex flex-col gap-2">
            <div className="flex items-center gap-1.5">
              {succeeded ? (
                <CheckCircle2 className="size-3.5 text-[#0d9488] shrink-0" />
              ) : (
                <AlertCircle className="size-3.5 text-amber-500 shrink-0" />
              )}
              <span className="text-xs font-medium text-[#111827]">
                {succeeded ? "Import complete" : "Nothing imported"}
              </span>
            </div>

            {succeeded && (
              <div className="flex gap-3 text-[11px] text-[#6b7280]">
                <span>
                  <span className="font-semibold text-[#111827]">{result.companies_upserted}</span>{" "}
                  {result.companies_upserted === 1 ? "company" : "companies"}
                </span>
                <span>
                  <span className="font-semibold text-[#111827]">{result.people_upserted}</span>{" "}
                  {result.people_upserted === 1 ? "person" : "people"}
                </span>
                <span className="text-[#9ca3af]">{result.rows_read} rows read</span>
              </div>
            )}

            {result.errors.length > 0 && (
              <ul className="text-[10px] space-y-0.5 max-h-24 overflow-y-auto">
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
