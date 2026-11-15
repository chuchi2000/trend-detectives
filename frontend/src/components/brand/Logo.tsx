/**
 * Símbolo del Atlas: un planeta atravesado por una franja de seis píxeles,
 * la huella de un satélite que mide la superficie.
 */
export function LogoMark({ size = 34, theme = "claro" }: { size?: number; theme?: "claro" | "oscuro" }) {
  const dark = theme === "oscuro";
  const ring = dark ? "#E6EEF0" : "#10302A";
  const top = dark ? ["#7FD1DC", "#1E9C96", "#4A9BC4"] : ["#1E9C96", "#1D6B4F", "#155E83"];
  const bottom = dark ? ["#1E9C96", "#4A9BC4", "#E6EEF0"] : ["#1D6B4F", "#155E83", "#10302A"];
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <circle cx="20" cy="20" r="14" fill="none" stroke={ring} strokeWidth="2.5" />
      <g transform="rotate(-35 20 20)">
        {[10, 17, 24].map((x, i) => (
          <rect key={`t${x}`} x={x} y="13.5" width="6" height="6" rx="1" fill={top[i]} />
        ))}
        {[10, 17, 24].map((x, i) => (
          <rect key={`b${x}`} x={x} y="20.5" width="6" height="6" rx="1" fill={bottom[i]} />
        ))}
      </g>
    </svg>
  );
}

export function LogoLockup({ theme = "claro" }: { theme?: "claro" | "oscuro" }) {
  return (
    <span className="inline-flex items-center gap-3">
      <LogoMark theme={theme} />
      <span className="font-display text-[17px] leading-tight font-bold [font-stretch:112%]">
        Atlas Ambiental de México
      </span>
    </span>
  );
}
