import { useState, useCallback } from "react";
import {
  PlusCircle, Loader2, CheckCircle2, AlertCircle,
  Users, Building2, Calendar, Mail, ChevronRight, ChevronLeft,
} from "lucide-react";
import { CsvImportWidget } from "@/components/CsvImportWidget";

// ---------------------------------------------------------------------------
// Shared field components
// ---------------------------------------------------------------------------

function Field({
  label, name, value, onChange, placeholder, type = "text",
}: {
  label: string; name: string; value: string;
  onChange: (name: string, value: string) => void;
  placeholder?: string; type?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-[#374151]">{label}</label>
      <input
        type={type} value={value}
        onChange={(e) => onChange(name, e.target.value)}
        placeholder={placeholder}
        className="px-3 py-2 text-sm border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0d9488]/30 focus:border-[#0d9488] bg-white placeholder:text-[#d1d5db]"
      />
    </div>
  );
}

function SelectField({
  label, name, value, onChange, options,
}: {
  label: string; name: string; value: string;
  onChange: (name: string, value: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-[#374151]">{label}</label>
      <select
        value={value} onChange={(e) => onChange(name, e.target.value)}
        className="px-3 py-2 text-sm border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0d9488]/30 focus:border-[#0d9488] bg-white text-[#374151]"
      >
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step definitions
// ---------------------------------------------------------------------------

const STEPS = [
  { id: "person", label: "Person", icon: Users },
  { id: "company", label: "Company", icon: Building2 },
  { id: "demo", label: "Demo", icon: Calendar },
  { id: "email", label: "Email", icon: Mail },
] as const;

type StepId = typeof STEPS[number]["id"];

function hasData(obj: Record<string, string | number | undefined>): boolean {
  return Object.values(obj).some((v) => v !== "" && v !== undefined);
}

// ---------------------------------------------------------------------------
// Individual step forms (stateless — data/onChange passed in)
// ---------------------------------------------------------------------------

function PersonStep({
  data, onChange,
}: { data: Record<string, string>; onChange: (k: string, v: string) => void }) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-[#6b7280]">
        Enter what you know. If email or title is missing, the AI will search for the rest.
      </p>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Name" name="name" value={data.name} onChange={onChange} placeholder="Jane Smith" />
        <Field label="Email" name="email" value={data.email} onChange={onChange} placeholder="jane@company.com" type="email" />
        <Field label="Title" name="title" value={data.title} onChange={onChange} placeholder="VP of Sales" />
        <Field label="Phone" name="phone" value={data.phone} onChange={onChange} placeholder="+1 (555) 000-0000" />
        <div className="col-span-2">
          <Field label="LinkedIn URL" name="linkedin" value={data.linkedin} onChange={onChange} placeholder="https://linkedin.com/in/..." />
        </div>
        <SelectField
          label="Stage" name="stage" value={data.stage} onChange={onChange}
          options={[
            { value: "prospect", label: "Prospect" },
            { value: "contacted", label: "Contacted" },
            { value: "demo_scheduled", label: "Demo Scheduled" },
            { value: "client", label: "Client" },
          ]}
        />
      </div>
    </div>
  );
}

function CompanyStep({
  data, onChange,
}: { data: Record<string, string>; onChange: (k: string, v: string) => void }) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-[#6b7280]">
        If website or industry is missing, the AI will search for the rest.
      </p>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Company Name" name="name" value={data.name} onChange={onChange} placeholder="Acme Corp" />
        <Field label="Website" name="website" value={data.website} onChange={onChange} placeholder="https://acme.com" />
        <Field label="Industry" name="industry" value={data.industry} onChange={onChange} placeholder="SaaS, Healthcare…" />
        <Field label="Phone" name="phone" value={data.phone} onChange={onChange} placeholder="+1 (555) 000-0000" />
        <Field label="Address" name="address" value={data.address} onChange={onChange} placeholder="123 Main St" />
        <Field label="City" name="city" value={data.city} onChange={onChange} placeholder="Denver" />
        <Field label="State" name="state" value={data.state} onChange={onChange} placeholder="CO" />
        <Field label="Zip" name="zip" value={data.zip} onChange={onChange} placeholder="80202" />
        <Field label="Employee Count" name="employee_count" value={data.employee_count} onChange={onChange} placeholder="50" type="number" />
      </div>
    </div>
  );
}

function DemoStep({
  data, onChange,
}: { data: Record<string, string>; onChange: (k: string, v: string) => void }) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-[#6b7280]">
        Schedule a demo. Person and company will be linked automatically from your earlier entries.
        Only fill in IDs if you want to link to a different existing record.
      </p>
      <div className="grid grid-cols-2 gap-3">
        <SelectField
          label="Type" name="type" value={data.type} onChange={onChange}
          options={[
            { value: "discovery", label: "Discovery" },
            { value: "tech", label: "Tech" },
            { value: "pricing", label: "Pricing" },
            { value: "onboarding", label: "Onboarding" },
          ]}
        />
        <SelectField
          label="Status" name="status" value={data.status} onChange={onChange}
          options={[
            { value: "scheduled", label: "Scheduled" },
            { value: "completed", label: "Completed" },
            { value: "canceled", label: "Canceled" },
            { value: "missed", label: "Missed" },
          ]}
        />
        <Field label="Date & Time" name="date" value={data.date} onChange={onChange} type="datetime-local" />
        <Field label="Person ID (optional override)" name="people_id" value={data.people_id} onChange={onChange} placeholder="UUID" />
        <Field label="Company ID (optional override)" name="company_id" value={data.company_id} onChange={onChange} placeholder="UUID" />
      </div>
    </div>
  );
}

function EmailStep({
  data, onChange,
}: { data: Record<string, string>; onChange: (k: string, v: string) => void }) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-[#6b7280]">
        Log an email or message. It will be linked to the person entered above.
      </p>
      <div className="grid grid-cols-2 gap-3">
        <Field label="From Email" name="from_email" value={data.from_email} onChange={onChange} placeholder="sender@example.com" type="email" />
        <Field label="From Name" name="from_name" value={data.from_name} onChange={onChange} placeholder="John Doe" />
        <div className="col-span-2">
          <Field label="Subject" name="subject" value={data.subject} onChange={onChange} placeholder="Re: Our meeting" />
        </div>
        <SelectField
          label="Category" name="category" value={data.category} onChange={onChange}
          options={[
            { value: "manual", label: "Manual Review" },
            { value: "interested", label: "Interested" },
            { value: "not_interested", label: "Not Interested" },
            { value: "demo_request", label: "Demo Request" },
            { value: "other", label: "Other" },
          ]}
        />
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-[#374151]">Body Snippet</label>
        <textarea
          value={data.body_snippet} onChange={(e) => onChange("body_snippet", e.target.value)}
          placeholder="First ~500 characters of the email body…"
          rows={3}
          className="px-3 py-2 text-sm border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0d9488]/30 focus:border-[#0d9488] bg-white placeholder:text-[#d1d5db] resize-none"
        />
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-[#374151]">Note</label>
        <textarea
          value={data.note} onChange={(e) => onChange("note", e.target.value)}
          placeholder="Optional internal note…"
          rows={2}
          className="px-3 py-2 text-sm border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0d9488]/30 focus:border-[#0d9488] bg-white placeholder:text-[#d1d5db] resize-none"
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Submission logic
// ---------------------------------------------------------------------------

type SubmitPhase =
  | { status: "idle" }
  | { status: "submitting"; step: StepId }
  | { status: "enriching"; step: StepId; jobId: string; jobStatus: string }
  | { status: "done" }
  | { status: "error"; message: string };

async function pollJob(jobId: string): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const iv = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        const job = await res.json();
        if (job.status === "completed") { clearInterval(iv); resolve(job.result); }
        else if (job.status === "failed") { clearInterval(iv); reject(new Error(job.error || "Job failed")); }
      } catch (e) { clearInterval(iv); reject(e); }
    }, 2000);
  });
}

// ---------------------------------------------------------------------------
// Main wizard page
// ---------------------------------------------------------------------------

const EMPTY_PERSON = { name: "", email: "", title: "", phone: "", linkedin: "", stage: "prospect" };
const EMPTY_COMPANY = { name: "", website: "", industry: "", address: "", city: "", state: "", zip: "", phone: "", employee_count: "" };
const EMPTY_DEMO = { type: "discovery", status: "scheduled", date: "", people_id: "", company_id: "" };
const EMPTY_EMAIL = { from_email: "", from_name: "", subject: "", body_snippet: "", category: "manual", note: "" };

export function AddPage() {
  const [step, setStep] = useState(0);
  const [personData, setPersonData] = useState({ ...EMPTY_PERSON });
  const [companyData, setCompanyData] = useState({ ...EMPTY_COMPANY });
  const [demoData, setDemoData] = useState({ ...EMPTY_DEMO });
  const [emailData, setEmailData] = useState({ ...EMPTY_EMAIL });
  const [phase, setPhase] = useState<SubmitPhase>({ status: "idle" });

  const updatePerson = useCallback((k: string, v: string) => setPersonData((d) => ({ ...d, [k]: v })), []);
  const updateCompany = useCallback((k: string, v: string) => setCompanyData((d) => ({ ...d, [k]: v })), []);
  const updateDemo = useCallback((k: string, v: string) => setDemoData((d) => ({ ...d, [k]: v })), []);
  const updateEmail = useCallback((k: string, v: string) => setEmailData((d) => ({ ...d, [k]: v })), []);

  const isLastStep = step === STEPS.length - 1;

  // Validate that at least one field across all steps has data
  const hasAnyData =
    hasData(personData) || hasData(companyData) || hasData(demoData) || hasData(emailData);

  const handleSubmit = useCallback(async () => {
    if (!hasAnyData) {
      setPhase({ status: "error", message: "Please fill in at least one field across any step." });
      return;
    }

    setPhase({ status: "submitting", step: "person" });

    let personId: string | undefined;
    let companyId: string | undefined;

    // --- 1. Person ---
    if (hasData(personData)) {
      const payload = Object.fromEntries(Object.entries(personData).filter(([, v]) => v !== ""));
      try {
        const res = await fetch("/api/add/person", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const json = await res.json();
        if (!res.ok) throw new Error(json.detail || "Failed to save person");

        if (json.enriching) {
          setPhase({ status: "enriching", step: "person", jobId: json.job_id, jobStatus: "running" });
          const result = await pollJob(json.job_id) as Record<string, string>;
          personId = result?.id as string | undefined;
        } else {
          personId = json.entity?.id as string | undefined;
        }
      } catch (e) {
        setPhase({ status: "error", message: `Person: ${e instanceof Error ? e.message : String(e)}` });
        return;
      }
    }

    // --- 2. Company ---
    setPhase({ status: "submitting", step: "company" });
    if (hasData(companyData)) {
      // Merge company_name from person step if company name not entered
      const mergedCompany = { ...companyData };
      if (!mergedCompany.name && personData.name) {
        // skip — no company name to use
      }
      const payload = Object.fromEntries(Object.entries(mergedCompany).filter(([, v]) => v !== ""));
      if (Object.keys(payload).length > 0) {
        try {
          const res = await fetch("/api/add/company", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          const json = await res.json();
          if (!res.ok) throw new Error(json.detail || "Failed to save company");

          if (json.enriching) {
            setPhase({ status: "enriching", step: "company", jobId: json.job_id, jobStatus: "running" });
            const result = await pollJob(json.job_id) as Record<string, string>;
            companyId = result?.id as string | undefined;
          } else {
            companyId = json.entity?.id as string | undefined;
          }
        } catch (e) {
          setPhase({ status: "error", message: `Company: ${e instanceof Error ? e.message : String(e)}` });
          return;
        }
      }
    }

    // --- 3. Demo ---
    setPhase({ status: "submitting", step: "demo" });
    if (hasData(demoData)) {
      const payload: Record<string, string | undefined> = Object.fromEntries(
        Object.entries(demoData).filter(([, v]) => v !== "")
      );
      // Auto-link person + company from earlier steps
      if (personId && !payload.people_id) payload.people_id = personId;
      if (companyId && !payload.company_id) payload.company_id = companyId;

      if (Object.keys(payload).length > 0) {
        try {
          const res = await fetch("/api/add/demo", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          const json = await res.json();
          if (!res.ok) throw new Error(json.detail || "Failed to save demo");
        } catch (e) {
          setPhase({ status: "error", message: `Demo: ${e instanceof Error ? e.message : String(e)}` });
          return;
        }
      }
    }

    // --- 4. Email ---
    setPhase({ status: "submitting", step: "email" });
    if (hasData(emailData)) {
      const payload: Record<string, string | undefined> = Object.fromEntries(
        Object.entries(emailData).filter(([, v]) => v !== "")
      );
      // Auto-link person from earlier steps
      if (personId && !payload.people_id) payload.people_id = personId;

      if (Object.keys(payload).length > 0) {
        try {
          const res = await fetch("/api/add/email", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          const json = await res.json();
          if (!res.ok) throw new Error(json.detail || "Failed to save email");
        } catch (e) {
          setPhase({ status: "error", message: `Email: ${e instanceof Error ? e.message : String(e)}` });
          return;
        }
      }
    }

    setPhase({ status: "done" });
  }, [hasAnyData, personData, companyData, demoData, emailData]);

  const handleReset = () => {
    setPersonData({ ...EMPTY_PERSON });
    setCompanyData({ ...EMPTY_COMPANY });
    setDemoData({ ...EMPTY_DEMO });
    setEmailData({ ...EMPTY_EMAIL });
    setStep(0);
    setPhase({ status: "idle" });
  };

  const isSubmitting = phase.status === "submitting" || phase.status === "enriching";

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="max-w-6xl mx-auto px-6 py-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-lg bg-[#0d9488]/10">
          <PlusCircle className="size-5 text-[#0d9488]" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-[#111827]">Add Record</h1>
          <p className="text-sm text-[#9ca3af]">Fill in what you know — AI fills in the rest</p>
        </div>
      </div>

      {/* Two-column layout: wizard on left, CSV import on right */}
      <div className="flex gap-6 items-start">
        {/* ── Wizard ── */}
        <div className="flex-1 min-w-0">
          {phase.status === "done" ? (
            <div
              className="rounded-2xl border border-white/50 p-8 text-center flex flex-col items-center gap-4"
              style={{
                background: "rgba(255,255,255,0.7)",
                backdropFilter: "blur(12px)",
                boxShadow: "0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)",
              }}
            >
              <div className="w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center">
                <CheckCircle2 className="size-6 text-emerald-600" />
              </div>
              <div>
                <p className="text-base font-semibold text-[#111827]">All records saved</p>
                <p className="text-sm text-[#6b7280] mt-1">Everything was added and linked successfully.</p>
              </div>
              <button
                onClick={handleReset}
                className="px-4 py-2 rounded-lg bg-[#0d9488] text-white text-sm font-medium hover:bg-[#0f766e] transition-colors"
              >
                Add another
              </button>
            </div>
          ) : (
            <div
              className="rounded-2xl border border-white/50 overflow-hidden"
              style={{
                background: "rgba(255,255,255,0.7)",
                backdropFilter: "blur(12px)",
                boxShadow: "0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)",
              }}
            >
              {/* Step indicator */}
              <div className="flex border-b border-[#f3f4f6]">
                {STEPS.map(({ id, label, icon: Icon }, i) => {
                  const isActive = i === step;
                  const isDone = i < step;
                  return (
                    <button
                      key={id}
                      onClick={() => !isSubmitting && setStep(i)}
                      disabled={isSubmitting}
                      className={`flex-1 flex flex-col items-center gap-1 py-3 text-xs font-medium border-b-2 transition-colors ${
                        isActive
                          ? "border-[#0d9488] text-[#0d9488] bg-[#0d9488]/5"
                          : isDone
                          ? "border-[#0d9488]/30 text-[#0d9488]/60"
                          : "border-transparent text-[#9ca3af] hover:text-[#374151] hover:bg-[#f9fafb]"
                      } disabled:cursor-default`}
                    >
                      <div className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-semibold ${
                        isActive ? "bg-[#0d9488] text-white" :
                        isDone ? "bg-[#0d9488]/20 text-[#0d9488]" :
                        "bg-[#f3f4f6] text-[#9ca3af]"
                      }`}>
                        {isDone ? <CheckCircle2 className="size-4" /> : <Icon className="size-3.5" />}
                      </div>
                      <span className="hidden sm:block">{label}</span>
                    </button>
                  );
                })}
              </div>

              {/* Step content */}
              <div className="p-6">
                <div className="mb-4">
                  <h2 className="text-base font-semibold text-[#111827]">
                    Step {step + 1} of {STEPS.length}: {STEPS[step].label} Info
                  </h2>
                  <p className="text-xs text-[#9ca3af] mt-0.5">All fields are optional — skip any step you don't need</p>
                </div>

                {step === 0 && <PersonStep data={personData} onChange={updatePerson} />}
                {step === 1 && <CompanyStep data={companyData} onChange={updateCompany} />}
                {step === 2 && <DemoStep data={demoData} onChange={updateDemo} />}
                {step === 3 && <EmailStep data={emailData} onChange={updateEmail} />}

                {phase.status === "error" && (
                  <div className="flex items-start gap-2 mt-4 px-3 py-2.5 rounded-lg bg-red-50 border border-red-100 text-sm text-red-700">
                    <AlertCircle className="size-4 shrink-0 mt-0.5" />
                    {phase.message}
                  </div>
                )}

                {isSubmitting && (
                  <div className="flex items-center gap-2 mt-4 px-3 py-2.5 rounded-lg bg-amber-50 border border-amber-100 text-sm text-amber-700">
                    <Loader2 className="size-4 animate-spin shrink-0" />
                    {phase.status === "enriching"
                      ? `AI is searching for missing ${phase.step} info…`
                      : `Saving ${phase.step}…`}
                  </div>
                )}

                {/* Navigation */}
                <div className="flex items-center justify-between mt-6 pt-4 border-t border-[#f3f4f6]">
                  <button
                    onClick={() => setStep((s) => Math.max(0, s - 1))}
                    disabled={step === 0 || isSubmitting}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-[#6b7280] hover:text-[#374151] hover:bg-[#f3f4f6] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft className="size-4" />
                    Back
                  </button>

                  {isLastStep ? (
                    <button
                      onClick={handleSubmit}
                      disabled={isSubmitting || !hasAnyData}
                      className="flex items-center gap-2 px-5 py-2 rounded-lg bg-[#0d9488] text-white text-sm font-medium hover:bg-[#0f766e] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {isSubmitting ? (
                        <><Loader2 className="size-4 animate-spin" /> Saving…</>
                      ) : (
                        <><CheckCircle2 className="size-4" /> Submit All</>
                      )}
                    </button>
                  ) : (
                    <button
                      onClick={() => setStep((s) => Math.min(STEPS.length - 1, s + 1))}
                      disabled={isSubmitting}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#0d9488] text-white text-sm font-medium hover:bg-[#0f766e] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      Next
                      <ChevronRight className="size-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          <p className="mt-3 text-xs text-[#9ca3af] text-center">
            Click any step tab to go back and edit. Records will be linked automatically.
          </p>
        </div>

        {/* ── CSV Import sidebar ── */}
        <div className="w-72 shrink-0">
          <CsvImportWidget />
        </div>
      </div>
    </div>
  );
}
