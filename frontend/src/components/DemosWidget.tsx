import { RefreshCw, CalendarDays } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface Demo {
  id: string;
  type: string;
  date: string | null;
  status: string;
  event_id: string | null;
  person_name: string;
  person_email: string | null;
  company_name: string;
}

const DEMO_TYPE_LABELS: Record<string, string> = {
  discovery: "Discovery",
  tech: "Tech Demo",
  pricing: "Pricing",
  onboarding: "Onboarding",
  client: "Client Review",
};

const STATUS_BADGE: Record<string, "teal" | "green" | "gray"> = {
  scheduled: "teal",
  completed: "green",
  canceled: "gray",
  missed: "gray",
};

function formatDemoDate(isoString: string | null): string {
  if (!isoString) return "No date set";
  try {
    const d = new Date(isoString);
    return d.toLocaleString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

interface DemosWidgetProps {
  demos: Record<string, string>[];
  loading: boolean;
  onRefresh: () => void;
}

export function DemosWidget({ demos: rawDemos, loading, onRefresh }: DemosWidgetProps) {
  const demos = rawDemos as unknown as Demo[];

  return (
    <div className="panel overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-[#e5e7eb]">
        <h2 className="text-sm font-semibold text-[#111827] flex items-center gap-2">
          <CalendarDays className="size-4 text-[#0d9488]" />
          Upcoming Demos
          {demos.length > 0 && (
            <span className="ml-1 text-xs font-normal text-[#9ca3af]">
              {demos.length} total
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

      {loading && demos.length === 0 ? (
        <div className="px-5 py-8 text-center text-sm text-[#9ca3af]">Loading…</div>
      ) : demos.length === 0 ? (
        <div className="px-5 py-8 text-center text-sm text-[#9ca3af]">
          No demos scheduled. Add a row to the Demos sheet with status "scheduled".
        </div>
      ) : (
        <div className="divide-y divide-[#f3f4f6]">
          {demos.map((demo) => (
            <div key={demo.id} className="px-5 py-3.5 hover:bg-[#f9fafb] transition-colors">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold text-[#0d9488]">
                      {DEMO_TYPE_LABELS[demo.type] ?? demo.type}
                    </span>
                    <Badge variant={STATUS_BADGE[demo.status] ?? "gray"}>
                      {demo.status}
                    </Badge>
                    {demo.event_id && (
                      <span className="text-[10px] text-[#9ca3af] bg-[#f3f4f6] px-1.5 py-0.5 rounded">
                        on calendar
                      </span>
                    )}
                  </div>
                  <div className="text-sm font-medium text-[#111827] truncate">{demo.company_name}</div>
                  <div className="text-xs text-[#4b5563] truncate">{demo.person_name}</div>
                  <div className="text-xs text-[#9ca3af] mt-1">{formatDemoDate(demo.date)}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
