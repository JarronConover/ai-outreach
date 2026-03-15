import { useEffect, useState, useCallback } from "react";
import {
  LayoutDashboard, Building2, Users, Calendar, Mail,
  Server, Loader2, PlusCircle, ChevronLeft, ChevronRight, BookOpen,
} from "lucide-react";
import { OrchestratorSwitch } from "@/components/OrchestratorSwitch";
import { ProspectButton } from "@/components/ProspectButton";

export type Page = "dashboard" | "companies" | "people" | "demos" | "emails" | "add" | "references";

interface SidebarProps {
  currentPage: Page;
  onNavigate: (page: Page) => void;
  onJobComplete: () => void;
  collapsed: boolean;
  onToggle: () => void;
}

const NAV_ITEMS: { page: Page; label: string; icon: React.ElementType }[] = [
  { page: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { page: "companies", label: "Companies", icon: Building2 },
  { page: "people",    label: "People",    icon: Users },
  { page: "demos",     label: "Demos",     icon: Calendar },
  { page: "emails",    label: "Emails",    icon: Mail },
  { page: "add",        label: "Add Record",  icon: PlusCircle },
  { page: "references", label: "References",  icon: BookOpen },
];

type BackendState = "online" | "offline" | "starting" | "checking";

export function Sidebar({ currentPage, onNavigate, onJobComplete, collapsed, onToggle }: SidebarProps) {
  const [backendState, setBackendState] = useState<BackendState>("checking");

  const checkBackend = useCallback(async () => {
    try {
      const res = await fetch("/api/health", { signal: AbortSignal.timeout(2000) });
      setBackendState(res.ok ? "online" : "offline");
    } catch {
      setBackendState("offline");
    }
  }, []);

  useEffect(() => {
    checkBackend();
    const id = setInterval(checkBackend, 5000);
    return () => clearInterval(id);
  }, [checkBackend]);

  const handleStartBackend = async () => {
    setBackendState("starting");
    try {
      await fetch("/dev/start-backend", { method: "POST" });
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        try {
          const res = await fetch("/api/health", { signal: AbortSignal.timeout(1500) });
          if (res.ok) { setBackendState("online"); clearInterval(poll); }
        } catch { /* still starting */ }
        if (attempts > 20) { clearInterval(poll); setBackendState("offline"); }
      }, 1500);
    } catch {
      setBackendState("offline");
    }
  };

  const backendDot = {
    online: "bg-emerald-500", offline: "bg-red-400",
    starting: "bg-amber-400", checking: "bg-[#d1d5db]",
  }[backendState];

  return (
    <aside
      className="fixed top-0 left-0 z-30 h-full flex flex-col transition-all duration-200"
      style={{
        width: collapsed ? 72 : 288,
        background: "rgba(255,255,255,0.82)",
        backdropFilter: "blur(24px) saturate(180%)",
        WebkitBackdropFilter: "blur(24px) saturate(180%)",
        borderRight: "1px solid rgba(255,255,255,0.5)",
        overflow: "hidden",
      }}
    >
      {/* ── Logo row — toggle always lives here ── */}
      <div className={`h-16 shrink-0 flex items-center border-b border-white/50 ${collapsed ? "justify-center" : "px-5 justify-between"}`}>
        {collapsed ? (
          <button
            onClick={onToggle}
            title="Expand sidebar"
            className="p-1.5 rounded-md text-[#9ca3af] hover:text-[#374151] hover:bg-[#f3f4f6] transition-colors"
          >
            <ChevronRight className="size-4" />
          </button>
        ) : (
          <>
            <div className="flex items-center gap-2.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#0d9488] shrink-0" />
              <span className="text-base font-semibold text-[#111827] tracking-tight whitespace-nowrap">Scout</span>
            </div>
            <button
              onClick={onToggle}
              title="Collapse sidebar"
              className="p-1.5 rounded-md text-[#9ca3af] hover:text-[#374151] hover:bg-[#f3f4f6] transition-colors"
            >
              <ChevronLeft className="size-4" />
            </button>
          </>
        )}
      </div>

      {/* ── Nav ── */}
      <nav className={`flex-1 py-4 flex flex-col gap-1 overflow-y-auto ${collapsed ? "px-2 items-center" : "px-3"}`}>
        {!collapsed && (
          <p className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-widest text-[#9ca3af]">
            Navigation
          </p>
        )}
        {NAV_ITEMS.map(({ page, label, icon: Icon }) =>
          collapsed ? (
            <button
              key={page}
              onClick={() => onNavigate(page)}
              title={label}
              className={`flex items-center justify-center w-10 h-10 rounded-lg transition-colors ${
                currentPage === page
                  ? "bg-[#0d9488]/10 text-[#0d9488]"
                  : "text-[#9ca3af] hover:bg-[#f3f4f6] hover:text-[#374151]"
              }`}
            >
              <Icon className="size-5" />
            </button>
          ) : (
            <button
              key={page}
              onClick={() => onNavigate(page)}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-left w-full ${
                currentPage === page
                  ? "bg-[#0d9488]/10 text-[#0d9488]"
                  : "text-[#374151] hover:bg-[#f3f4f6] hover:text-[#111827]"
              }`}
            >
              <Icon className={`size-4 shrink-0 ${currentPage === page ? "text-[#0d9488]" : "text-[#9ca3af]"}`} />
              {label}
            </button>
          )
        )}
      </nav>

      {/* ── Services / bottom controls ── */}
      <div className={`flex flex-col border-t border-white/50 pt-3 pb-4 ${collapsed ? "px-2 gap-2 items-center" : "px-3 gap-3"}`}>
        {!collapsed && (
          <p className="px-2 text-[10px] font-semibold uppercase tracking-widest text-[#9ca3af]">
            Services
          </p>
        )}

        <ProspectButton onComplete={onJobComplete} collapsed={collapsed} />
        <OrchestratorSwitch collapsed={collapsed} />

        {/* Backend status */}
        {collapsed ? (
          <div className="flex justify-center py-1" title={`Backend: ${backendState}`}>
            <span className={`w-2.5 h-2.5 rounded-full ${backendDot}`} />
          </div>
        ) : (
          <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-white/60 border border-white/50 shadow-sm">
            <div className="flex items-center gap-2.5">
              <Server className="size-4 text-[#6b7280]" />
              <div>
                <p className="text-xs font-semibold text-[#111827]">Backend API</p>
                <p className="text-[10px] text-[#9ca3af] capitalize">{backendState}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${backendDot}`} />
              {backendState === "offline" && (
                <button
                  onClick={handleStartBackend}
                  className="text-[10px] font-medium px-2 py-1 rounded-md bg-[#0d9488] text-white hover:bg-[#0f766e] transition-colors"
                >
                  Start
                </button>
              )}
              {backendState === "starting" && <Loader2 className="size-3 text-[#0d9488] animate-spin" />}
            </div>
          </div>
        )}

      </div>
    </aside>
  );
}
