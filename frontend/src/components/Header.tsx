import { LogOut } from "lucide-react";
import { supabase } from "@/lib/supabase";

interface HeaderProps {
  sidebarWidth: number;
}

export function Header({ sidebarWidth }: HeaderProps) {
  const handleLogout = () => supabase.auth.signOut();

  return (
    <div
      className="fixed top-0 z-20 flex items-center justify-between pt-3 px-4 pointer-events-none transition-all duration-200"
      style={{ left: sidebarWidth, right: 0 }}
    >
      {/* Centre pill */}
      <div className="flex-1 flex justify-center">
        <div
          className="flex items-center gap-2.5 px-5 py-2.5 pointer-events-auto"
          style={{
            background: "rgba(255,255,255,0.55)",
            backdropFilter: "blur(28px) saturate(200%)",
            WebkitBackdropFilter: "blur(28px) saturate(200%)",
            borderRadius: "9999px",
            border: "1px solid rgba(255,255,255,0.7)",
            boxShadow: "0 2px 16px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.04)",
          }}
        >
          <span className="w-2 h-2 rounded-full bg-[#0d9488] shrink-0" />
          <span className="text-sm font-semibold text-[#111827] tracking-tight">Scout</span>
          <span className="w-px h-3.5 bg-[#e5e7eb]" />
          <span className="text-xs text-[#6b7280]">AI Sales Pipeline</span>
        </div>
      </div>

      {/* Logout button */}
      <button
        onClick={handleLogout}
        title="Sign out"
        className="pointer-events-auto flex items-center justify-center w-8 h-8 rounded-full text-[#9ca3af] hover:text-[#374151] hover:bg-white/60 transition-colors"
        style={{
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
        }}
      >
        <LogOut className="size-3.5" />
      </button>
    </div>
  );
}
