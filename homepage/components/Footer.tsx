import Link from "next/link";

export function Footer() {
  return (
    <footer className="py-16 px-6 bg-ash">
      <div className="max-w-page mx-auto">
        <div className="grid md:grid-cols-4 gap-10">
          <div className="md:col-span-2">
            <span className="font-display text-[15px] tracking-tight text-graphite">
              CORES
            </span>
            <p className="font-sans text-[13px] text-slate mt-2 max-w-xs leading-relaxed">
              Deterministic cognitive operating system for robotics. One battery. One CPU. One chance.
            </p>
          </div>
          <div>
            <span className="font-display text-[12px] tracking-tight text-brass uppercase">Architecture</span>
            <div className="mt-4 space-y-2">
              <Link href="#modules" className="block font-sans text-[13px] text-slate hover:text-graphite transition-colors">Modules</Link>
              <Link href="#policies" className="block font-sans text-[13px] text-slate hover:text-graphite transition-colors">Policies</Link>
              <Link href="#visualizations" className="block font-sans text-[13px] text-slate hover:text-graphite transition-colors">Telemetry</Link>
            </div>
          </div>
          <div>
            <span className="font-display text-[12px] tracking-tight text-brass uppercase">Resources</span>
            <div className="mt-4 space-y-2">
              <Link href="/simulator" className="block font-sans text-[13px] text-slate hover:text-graphite transition-colors">Simulator</Link>
              <Link href="/design" className="block font-sans text-[13px] text-slate hover:text-graphite transition-colors">Design</Link>
            </div>
          </div>
        </div>
        <div className="mt-12 pt-8 border-t border-mist flex items-center justify-between">
          <span className="font-sans text-[12px] text-slate">CORES v0.1</span>
          <span className="font-sans text-[12px] text-slate">Deterministic by design</span>
        </div>
      </div>
    </footer>
  );
}
