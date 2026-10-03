export default function Waveform({
  active,
  bars = 44,
  className = "h-16",
}: {
  active: boolean;
  bars?: number;
  className?: string;
}) {
  return (
    <div className={`flex items-center justify-center gap-[3px] ${className}`}>
      {Array.from({ length: bars }).map((_, i) => (
        <span
          key={i}
          className="w-[3px] rounded-full bg-gradient-to-t from-blue-500 to-cyan-300"
          style={{
            height: active ? `${14 + Math.abs(Math.sin(i * 1.27)) * 44}px` : "5px",
            animation: active
              ? `wave ${0.66 + (i % 5) * 0.13}s ease-in-out ${i * 0.028}s infinite`
              : "none",
            opacity: active ? 1 : 0.3,
            transition: "height .35s, opacity .35s",
          }}
        />
      ))}
    </div>
  );
}
