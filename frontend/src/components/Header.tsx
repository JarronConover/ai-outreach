interface HeaderProps {
  sidebarWidth: number;
}

export function Header({ sidebarWidth }: HeaderProps) {
  return (
    <div
      className="fixed top-0 z-20 flex justify-center pt-3 pointer-events-none transition-all duration-200"
      style={{ left: sidebarWidth, right: 0 }}
    >
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
  );
}
