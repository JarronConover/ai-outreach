import { useState, useCallback, useEffect } from "react";
import { Header } from "@/components/Header";
import { RunPanel } from "@/components/RunPanel";
import { PendingActionsWidget } from "@/components/PendingActionsWidget";
import { NeedsResponseWidget } from "@/components/NeedsResponseWidget";
import { PeopleTable } from "@/components/PeopleTable";
import { DemosWidget } from "@/components/DemosWidget";
import { KpiCards } from "@/components/KpiCards";
import { CsvImportWidget } from "@/components/CsvImportWidget";

interface Stats {
  total_prospects: number;
  clients: number;
  demos_scheduled: number;
  demos_completed: number;
}

interface DashboardData {
  stats: Stats;
  people: Record<string, string>[];
  demos: Record<string, string>[];
}

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/dashboard");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDashboard(await res.json());
    } catch (err) {
      console.error("Failed to load dashboard", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard, refreshKey]);

  const handleJobComplete = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <div className="min-h-screen">
      <Header />
      <main className="max-w-7xl mx-auto px-6 py-6 flex flex-col gap-5">
        <KpiCards stats={dashboard?.stats ?? null} loading={loading} />
        <div className="flex gap-5 items-start">
          <aside className="w-72 shrink-0 flex flex-col gap-5">
            <RunPanel onJobComplete={handleJobComplete} />
            <CsvImportWidget />
          </aside>
          <div className="flex-1 min-w-0 flex flex-col gap-5">
            <PeopleTable people={dashboard?.people ?? []} loading={loading} onRefresh={fetchDashboard} />
            <DemosWidget demos={dashboard?.demos ?? []} loading={loading} onRefresh={fetchDashboard} />
            <NeedsResponseWidget />
            <PendingActionsWidget onJobComplete={handleJobComplete} />
          </div>
        </div>
      </main>
    </div>
  );
}
