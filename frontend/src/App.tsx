import { useState, useCallback } from "react";
import { Header } from "@/components/Header";
import { RunPanel } from "@/components/RunPanel";
import { PendingActionsWidget } from "@/components/PendingActionsWidget";
import { PeopleTable } from "@/components/PeopleTable";
import { DemosWidget } from "@/components/DemosWidget";
import { KpiCards } from "@/components/KpiCards";

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleJobComplete = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <div className="min-h-screen">
      <Header />
      <main className="max-w-7xl mx-auto px-6 py-6 flex flex-col gap-5">
        <KpiCards refreshKey={refreshKey} />
        <div className="flex gap-5 items-start">
          <aside className="w-72 shrink-0 flex flex-col gap-5">
            <RunPanel onJobComplete={handleJobComplete} />
          </aside>
          <div className="flex-1 min-w-0 flex flex-col gap-5">
            <PeopleTable refreshKey={refreshKey} />
            <DemosWidget refreshKey={refreshKey} />
            <PendingActionsWidget onJobComplete={handleJobComplete} />
          </div>
        </div>
      </main>
    </div>
  );
}
