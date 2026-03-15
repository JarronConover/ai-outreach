import { useState, useEffect, useCallback } from "react";
import {
  FileText, Settings2, ChevronDown, ChevronUp,
  Pencil, X, Save, Loader2, Plus, Trash2,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TemplateInfo {
  name: string;
  label: string;
  type: "html" | "text";
}

interface TemplateDetail extends TemplateInfo {
  content: string;
}

interface IcpConfig {
  industry?: string;
  company_size?: string;
  location?: string;
  num_companies?: number;
  num_people_per_company?: number;
  roles_to_target?: string[];
  pain_points?: string[];
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

function SectionHeader({ icon, title, count }: { icon: React.ReactNode; title: string; count?: number }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-[#0d9488]/10 text-[#0d9488]">
        {icon}
      </div>
      <h2 className="text-base font-semibold text-[#111827]">{title}</h2>
      {count !== undefined && (
        <span className="ml-1 text-xs font-medium text-[#9ca3af] bg-[#f3f4f6] px-2 py-0.5 rounded-full">
          {count}
        </span>
      )}
    </div>
  );
}

function SaveCancelRow({
  onSave, onCancel, saving,
}: { onSave: () => void; onCancel: () => void; saving: boolean }) {
  return (
    <div className="flex items-center gap-2 mt-4">
      <button
        onClick={onSave}
        disabled={saving}
        className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#0d9488] text-white text-sm font-medium hover:bg-[#0f766e] disabled:opacity-60 transition-colors"
      >
        {saving ? <Loader2 className="size-3.5 animate-spin" /> : <Save className="size-3.5" />}
        Save
      </button>
      <button
        onClick={onCancel}
        className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#f3f4f6] text-[#374151] text-sm font-medium hover:bg-[#e5e7eb] transition-colors"
      >
        <X className="size-3.5" />
        Cancel
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Template card
// ---------------------------------------------------------------------------

function TemplateCard({ info }: { info: TemplateInfo }) {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<TemplateDetail | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const load = useCallback(async () => {
    if (detail) return;
    setLoadingDetail(true);
    try {
      const res = await fetch(`/api/references/templates/${info.name}`);
      if (res.ok) {
        const data = await res.json();
        setDetail(data);
      }
    } finally {
      setLoadingDetail(false);
    }
  }, [detail, info.name]);

  const handleToggle = () => {
    if (!open) load();
    setOpen((o) => !o);
    setEditing(false);
  };

  const handleEdit = () => {
    if (!detail) return;
    setDraft(detail.content);
    setEditing(true);
  };

  const handleCancel = () => {
    setEditing(false);
    setDraft("");
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`/api/references/templates/${info.name}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: draft }),
      });
      if (res.ok) {
        setDetail((d) => d ? { ...d, content: draft } : d);
        setEditing(false);
      }
    } finally {
      setSaving(false);
    }
  };

  // Strip HTML tags for a clean read-only preview
  const readableContent = (content: string) =>
    info.type === "html"
      ? content.replace(/<[^>]*>/g, "").replace(/\s{2,}/g, "\n").trim()
      : content;

  return (
    <div className="rounded-xl border border-[#e5e7eb] bg-white/70 overflow-hidden transition-shadow hover:shadow-sm">
      {/* Header row */}
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between px-5 py-4 text-left"
      >
        <div className="flex items-center gap-3">
          <FileText className="size-4 text-[#0d9488] shrink-0" />
          <span className="text-sm font-medium text-[#111827]">{info.label}</span>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[#9ca3af] bg-[#f3f4f6] px-1.5 py-0.5 rounded">
            {info.type === "html" ? "HTML" : "TXT"}
          </span>
        </div>
        {open
          ? <ChevronUp className="size-4 text-[#9ca3af]" />
          : <ChevronDown className="size-4 text-[#9ca3af]" />}
      </button>

      {/* Expanded body */}
      {open && (
        <div className="border-t border-[#f3f4f6] px-5 pb-5 pt-4">
          {loadingDetail ? (
            <div className="flex items-center gap-2 text-sm text-[#9ca3af]">
              <Loader2 className="size-4 animate-spin" /> Loading…
            </div>
          ) : detail ? (
            editing ? (
              <>
                <p className="text-xs text-[#6b7280] mb-2">
                  {info.type === "html"
                    ? "Edit the raw HTML below. Use {placeholders} for dynamic values."
                    : "Edit the template below. Use {placeholders} for dynamic values."}
                </p>
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  rows={16}
                  className="w-full rounded-lg border border-[#e5e7eb] bg-[#fafafa] px-4 py-3 text-sm font-mono text-[#374151] focus:outline-none focus:ring-2 focus:ring-[#0d9488]/30 resize-y"
                />
                <SaveCancelRow onSave={handleSave} onCancel={handleCancel} saving={saving} />
              </>
            ) : (
              <>
                <pre className="whitespace-pre-wrap text-sm text-[#374151] leading-relaxed bg-[#f9fafb] rounded-lg px-4 py-3 border border-[#f3f4f6] max-h-72 overflow-y-auto">
                  {readableContent(detail.content)}
                </pre>
                <button
                  onClick={handleEdit}
                  className="mt-3 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#f3f4f6] text-[#374151] text-xs font-medium hover:bg-[#e5e7eb] transition-colors"
                >
                  <Pencil className="size-3" /> Edit template
                </button>
              </>
            )
          ) : null}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ICP Config card
// ---------------------------------------------------------------------------

function IcpCard() {
  const [open, setOpen] = useState(false);
  const [config, setConfig] = useState<IcpConfig | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<IcpConfig>({});
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (config) return;
    setLoading(true);
    try {
      const res = await fetch("/api/references/icp");
      if (res.ok) setConfig(await res.json());
    } finally {
      setLoading(false);
    }
  }, [config]);

  const handleToggle = () => {
    if (!open) load();
    setOpen((o) => !o);
    setEditing(false);
  };

  const handleEdit = () => {
    if (!config) return;
    setDraft(JSON.parse(JSON.stringify(config)));
    setEditing(true);
  };

  const handleCancel = () => setEditing(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch("/api/references/icp", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data: draft }),
      });
      if (res.ok) {
        setConfig(draft);
        setEditing(false);
      }
    } finally {
      setSaving(false);
    }
  };

  const setField = (key: string, value: unknown) =>
    setDraft((d) => ({ ...d, [key]: value }));

  const setListItem = (key: "roles_to_target" | "pain_points", idx: number, val: string) =>
    setDraft((d) => {
      const arr = [...(d[key] ?? [])];
      arr[idx] = val;
      return { ...d, [key]: arr };
    });

  const addListItem = (key: "roles_to_target" | "pain_points") =>
    setDraft((d) => ({ ...d, [key]: [...(d[key] ?? []), ""] }));

  const removeListItem = (key: "roles_to_target" | "pain_points", idx: number) =>
    setDraft((d) => {
      const arr = (d[key] ?? []).filter((_, i) => i !== idx);
      return { ...d, [key]: arr };
    });

  return (
    <div className="rounded-xl border border-[#e5e7eb] bg-white/70 overflow-hidden transition-shadow hover:shadow-sm">
      {/* Header */}
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between px-5 py-4 text-left"
      >
        <div className="flex items-center gap-3">
          <Settings2 className="size-4 text-[#0d9488] shrink-0" />
          <span className="text-sm font-medium text-[#111827]">Ideal Customer Profile</span>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[#9ca3af] bg-[#f3f4f6] px-1.5 py-0.5 rounded">
            JSON
          </span>
        </div>
        {open
          ? <ChevronUp className="size-4 text-[#9ca3af]" />
          : <ChevronDown className="size-4 text-[#9ca3af]" />}
      </button>

      {/* Body */}
      {open && (
        <div className="border-t border-[#f3f4f6] px-5 pb-5 pt-4">
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-[#9ca3af]">
              <Loader2 className="size-4 animate-spin" /> Loading…
            </div>
          ) : config ? (
            editing ? (
              <IcpEditForm
                draft={draft}
                setField={setField}
                setListItem={setListItem}
                addListItem={addListItem}
                removeListItem={removeListItem}
                onSave={handleSave}
                onCancel={handleCancel}
                saving={saving}
              />
            ) : (
              <IcpReadView config={config} onEdit={handleEdit} />
            )
          ) : null}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ICP read view
// ---------------------------------------------------------------------------

function IcpReadView({ config, onEdit }: { config: IcpConfig; onEdit: () => void }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-4">
        {config.industry && (
          <ReadField label="Industry" value={config.industry as string} />
        )}
        {config.company_size && (
          <ReadField label="Company Size" value={config.company_size as string} />
        )}
        {config.location && (
          <ReadField label="Location" value={config.location as string} />
        )}
        {config.num_companies !== undefined && (
          <ReadField label="Companies per Run" value={String(config.num_companies)} />
        )}
        {config.num_people_per_company !== undefined && (
          <ReadField label="People per Company" value={String(config.num_people_per_company)} />
        )}
      </div>

      {config.roles_to_target && config.roles_to_target.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-[#6b7280] uppercase tracking-wider mb-2">Target Roles</p>
          <div className="flex flex-wrap gap-1.5">
            {config.roles_to_target.map((r) => (
              <span key={r} className="px-2.5 py-1 rounded-full bg-[#0d9488]/10 text-[#0d9488] text-xs font-medium">
                {r}
              </span>
            ))}
          </div>
        </div>
      )}

      {config.pain_points && config.pain_points.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-[#6b7280] uppercase tracking-wider mb-2">Pain Points</p>
          <ul className="flex flex-col gap-1.5">
            {config.pain_points.map((p, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-[#374151]">
                <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[#0d9488] shrink-0" />
                {p}
              </li>
            ))}
          </ul>
        </div>
      )}

      <button
        onClick={onEdit}
        className="self-start flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#f3f4f6] text-[#374151] text-xs font-medium hover:bg-[#e5e7eb] transition-colors"
      >
        <Pencil className="size-3" /> Edit ICP
      </button>
    </div>
  );
}

function ReadField({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[#f9fafb] rounded-lg px-4 py-3 border border-[#f3f4f6]">
      <p className="text-[10px] font-semibold text-[#9ca3af] uppercase tracking-wider mb-0.5">{label}</p>
      <p className="text-sm font-medium text-[#111827]">{value}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ICP edit form
// ---------------------------------------------------------------------------

interface IcpEditFormProps {
  draft: IcpConfig;
  setField: (key: string, value: unknown) => void;
  setListItem: (key: "roles_to_target" | "pain_points", idx: number, val: string) => void;
  addListItem: (key: "roles_to_target" | "pain_points") => void;
  removeListItem: (key: "roles_to_target" | "pain_points", idx: number) => void;
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
}

function IcpEditForm({
  draft, setField, setListItem, addListItem, removeListItem, onSave, onCancel, saving,
}: IcpEditFormProps) {
  return (
    <div className="flex flex-col gap-5">
      {/* Basic fields */}
      <div className="grid grid-cols-2 gap-4">
        <EditField
          label="Industry"
          value={(draft.industry as string) ?? ""}
          onChange={(v) => setField("industry", v)}
          placeholder="e.g. Personal Injury Law Firms"
        />
        <EditField
          label="Company Size"
          value={(draft.company_size as string) ?? ""}
          onChange={(v) => setField("company_size", v)}
          placeholder="e.g. 10-250 employees"
        />
        <EditField
          label="Location"
          value={(draft.location as string) ?? ""}
          onChange={(v) => setField("location", v)}
          placeholder="e.g. Utah"
        />
        <EditField
          label="Companies per Run"
          value={String(draft.num_companies ?? "")}
          onChange={(v) => setField("num_companies", v === "" ? undefined : Number(v))}
          placeholder="e.g. 5"
          type="number"
        />
        <EditField
          label="People per Company"
          value={String(draft.num_people_per_company ?? "")}
          onChange={(v) => setField("num_people_per_company", v === "" ? undefined : Number(v))}
          placeholder="e.g. 3"
          type="number"
        />
      </div>

      {/* Target roles */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-semibold text-[#6b7280] uppercase tracking-wider">Target Roles</p>
          <button
            onClick={() => addListItem("roles_to_target")}
            className="flex items-center gap-1 text-xs text-[#0d9488] hover:text-[#0f766e] font-medium"
          >
            <Plus className="size-3" /> Add role
          </button>
        </div>
        <div className="flex flex-col gap-2">
          {(draft.roles_to_target ?? []).map((role, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                value={role}
                onChange={(e) => setListItem("roles_to_target", i, e.target.value)}
                className="flex-1 rounded-lg border border-[#e5e7eb] bg-white px-3 py-2 text-sm text-[#374151] focus:outline-none focus:ring-2 focus:ring-[#0d9488]/30"
                placeholder="Role title"
              />
              <button
                onClick={() => removeListItem("roles_to_target", i)}
                className="p-1.5 rounded-md text-[#9ca3af] hover:text-red-400 hover:bg-red-50 transition-colors"
              >
                <Trash2 className="size-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Pain points */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-semibold text-[#6b7280] uppercase tracking-wider">Pain Points</p>
          <button
            onClick={() => addListItem("pain_points")}
            className="flex items-center gap-1 text-xs text-[#0d9488] hover:text-[#0f766e] font-medium"
          >
            <Plus className="size-3" /> Add point
          </button>
        </div>
        <div className="flex flex-col gap-2">
          {(draft.pain_points ?? []).map((point, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                value={point}
                onChange={(e) => setListItem("pain_points", i, e.target.value)}
                className="flex-1 rounded-lg border border-[#e5e7eb] bg-white px-3 py-2 text-sm text-[#374151] focus:outline-none focus:ring-2 focus:ring-[#0d9488]/30"
                placeholder="Pain point description"
              />
              <button
                onClick={() => removeListItem("pain_points", i)}
                className="p-1.5 rounded-md text-[#9ca3af] hover:text-red-400 hover:bg-red-50 transition-colors"
              >
                <Trash2 className="size-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>

      <SaveCancelRow onSave={onSave} onCancel={onCancel} saving={saving} />
    </div>
  );
}

function EditField({
  label, value, onChange, placeholder, type = "text",
}: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; type?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-semibold text-[#6b7280] uppercase tracking-wider">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="rounded-lg border border-[#e5e7eb] bg-white px-3 py-2 text-sm text-[#374151] focus:outline-none focus:ring-2 focus:ring-[#0d9488]/30"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function ReferencesPage() {
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(true);

  useEffect(() => {
    fetch("/api/references/templates")
      .then((r) => r.json())
      .then(setTemplates)
      .finally(() => setLoadingTemplates(false));
  }, []);

  return (
    <main className="max-w-3xl mx-auto px-6 py-8 flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-bold text-[#111827] tracking-tight">References</h1>
        <p className="text-sm text-[#6b7280] mt-1">Manage your ICP configuration and outreach templates.</p>
      </div>

      {/* ICP Config */}
      <section>
        <SectionHeader icon={<Settings2 className="size-4" />} title="ICP Configuration" />
        <IcpCard />
      </section>

      {/* Templates */}
      <section>
        <SectionHeader
          icon={<FileText className="size-4" />}
          title="Email Templates"
          count={templates.length}
        />
        {loadingTemplates ? (
          <div className="flex items-center gap-2 text-sm text-[#9ca3af]">
            <Loader2 className="size-4 animate-spin" /> Loading templates…
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {templates.map((t) => (
              <TemplateCard key={t.name} info={t} />
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
