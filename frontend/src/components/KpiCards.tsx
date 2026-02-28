import { Users, CalendarCheck, CalendarClock, Handshake } from "lucide-react";

interface Stats {
  total_prospects: number;
  clients: number;
  demos_scheduled: number;
  demos_completed: number;
}

interface KpiCardProps {
  label: string;
  value: number | string;
  icon: React.ReactNode;
}

function KpiCard({ label, value, icon }: KpiCardProps) {
  return (
    <div className="panel px-5 py-4 flex flex-col gap-1 flex-1 min-w-0">
      <div className="flex items-center justify-between">
        <p className="text-xs text-[#6b7280] font-medium truncate">{label}</p>
        <span className="text-[#9ca3af] shrink-0">{icon}</span>
      </div>
      <p className="text-2xl font-bold text-[#111827] leading-tight">{value}</p>
    </div>
  );
}

interface KpiCardsProps {
  stats: Stats | null;
  loading: boolean;
}

export function KpiCards({ stats, loading }: KpiCardsProps) {
  const v = (n: number | undefined) => (loading || stats == null ? "—" : (n ?? 0));

  return (
    <div className="flex gap-4">
      <KpiCard
        label="Total Contacts"
        value={v(stats?.total_prospects)}
        icon={<Users className="size-4" />}
      />
      <KpiCard
        label="Clients"
        value={v(stats?.clients)}
        icon={<Handshake className="size-4" />}
      />
      <KpiCard
        label="Demos Scheduled"
        value={v(stats?.demos_scheduled)}
        icon={<CalendarClock className="size-4" />}
      />
      <KpiCard
        label="Demos Completed"
        value={v(stats?.demos_completed)}
        icon={<CalendarCheck className="size-4" />}
      />
    </div>
  );
}
