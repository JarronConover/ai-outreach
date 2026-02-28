export function Header() {
  return (
    <header className="bg-white border-b border-[#e5e7eb] px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center gap-3">
        <span className="w-2.5 h-2.5 rounded-full bg-[#0d9488] shrink-0" />
        <h1 className="text-lg font-semibold text-[#111827] tracking-tight">
          AI Outreach
        </h1>
        <span className="text-[#9ca3af] text-sm ml-1">— Autonomous SDR</span>
      </div>
    </header>
  );
}
