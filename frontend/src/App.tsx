import { useState, useCallback } from "react";
import { Header } from "@/components/Header";
import { RunPanel } from "@/components/RunPanel";
import { PeopleTable } from "@/components/PeopleTable";

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleJobComplete = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <div className="min-h-screen bg-[#f3f4f6]">
      <Header />
      <main className="max-w-7xl mx-auto px-6 py-6 flex gap-5 items-start">
        <aside className="w-72 shrink-0">
          <RunPanel onJobComplete={handleJobComplete} />
        </aside>
        <div className="flex-1 min-w-0">
          <PeopleTable refreshKey={refreshKey} />
        </div>
      </main>
    </div>
  );
}
