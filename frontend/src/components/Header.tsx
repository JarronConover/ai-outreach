export function Header() {
  return (
    <header className="px-6 py-4 sticky top-0 z-10" style={{background: "rgba(255,255,255,0.55)", backdropFilter: "blur(20px) saturate(180%)", WebkitBackdropFilter: "blur(20px) saturate(180%)", borderBottom: "1px solid rgba(255,255,255,0.5)"}}>
      <div className="max-w-7xl mx-auto flex items-center gap-3">
        <span className="w-2.5 h-2.5 rounded-full bg-[#0d9488] shrink-0" />
        <h1 className="text-lg font-semibold text-[#111827] tracking-tight">
          Scout
        </h1>
        <span className="text-[#9ca3af] text-sm ml-1">— AI prospecting</span>
      </div>
    </header>
  );
}
