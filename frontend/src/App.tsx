import { useState, useCallback, useEffect } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";
import { initAuthFetch, resetAuthFetch, setAuthToken } from "@/lib/authFetch";
import { LoginPage } from "@/pages/LoginPage";
import { Header } from "@/components/Header";
import { Sidebar, type Page } from "@/components/Sidebar";
import { PendingActionsWidget } from "@/components/PendingActionsWidget";
import { NeedsResponseWidget } from "@/components/NeedsResponseWidget";
import { PeopleTable } from "@/components/PeopleTable";
import { DemosWidget } from "@/components/DemosWidget";
import { KpiCards } from "@/components/KpiCards";
import { CompaniesPage } from "@/pages/CompaniesPage";
import { PeoplePage } from "@/pages/PeoplePage";
import { DemosPage } from "@/pages/DemosPage";
import { EmailsPage } from "@/pages/EmailsPage";
import { AddPage } from "@/pages/AddPage";
import { ReferencesPage } from "@/pages/ReferencesPage";

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

// Sidebar widths in px — kept in sync with Tailwind classes used below
const SIDEBAR_EXPANDED = 288; // w-72
const SIDEBAR_COLLAPSED = 72;  // w-18

export default function App() {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [currentPage, setCurrentPage] = useState<Page>("dashboard");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  // ── Auth ────────────────────────────────────────────────────────────────────
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      if (data.session) {
        setAuthToken(data.session.access_token);
        initAuthFetch();
      }
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
      if (s) {
        setAuthToken(s.access_token);
        initAuthFetch();
      } else {
        resetAuthFetch();
      }
    });
    return () => listener.subscription.unsubscribe();
  }, []);

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
    if (session && currentPage === "dashboard") fetchDashboard();
  }, [session, fetchDashboard, refreshKey, currentPage]);

  const handleJobComplete = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  const sidebarWidth = sidebarCollapsed ? SIDEBAR_COLLAPSED : SIDEBAR_EXPANDED;

  // Still resolving session from storage
  if (session === undefined) return null;

  // Not logged in — show login page
  if (session === null) return <LoginPage />;

  return (
    <div className="min-h-screen">
      <Sidebar
        currentPage={currentPage}
        onNavigate={(page) => setCurrentPage(page)}
        onJobComplete={handleJobComplete}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((c) => !c)}
      />

      <Header sidebarWidth={sidebarWidth} />

      {/* Content area — transitions with sidebar */}
      <div
        className="pt-14 transition-all duration-200"
        style={{ marginLeft: sidebarWidth }}
      >
        {currentPage === "dashboard" && (
          <main className="max-w-7xl mx-auto px-6 py-6 flex flex-col gap-5">
            <KpiCards stats={dashboard?.stats ?? null} loading={loading} />
            <div className="flex-1 min-w-0 flex flex-col gap-5">
              <PeopleTable
                people={dashboard?.people ?? []}
                loading={loading}
                onRefresh={fetchDashboard}
              />
              <DemosWidget
                demos={dashboard?.demos ?? []}
                loading={loading}
                onRefresh={fetchDashboard}
              />
              <NeedsResponseWidget />
              <PendingActionsWidget onJobComplete={handleJobComplete} />
            </div>
          </main>
        )}

        {currentPage === "companies" && <CompaniesPage />}
        {currentPage === "people" && <PeoplePage />}
        {currentPage === "demos" && <DemosPage />}
        {currentPage === "emails" && <EmailsPage />}
        {currentPage === "add" && <AddPage />}
        {currentPage === "references" && <ReferencesPage />}
      </div>
    </div>
  );
}
