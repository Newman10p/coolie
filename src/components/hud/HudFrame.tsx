import type { ReactNode } from "react";
import { cn } from "../../utils/cn";

const corner = "pointer-events-none absolute h-5 w-5 border-blue-300/50";

/** Corner brackets + tick marks — reads as a spatial HUD overlay, not a web card. */
export default function HudFrame({
  children,
  className,
  active,
}: {
  children: ReactNode;
  className?: string;
  active?: boolean;
}) {
  return (
    <div className={cn("relative", className)}>
      <span className={cn(corner, "left-0 top-0 border-l-2 border-t-2 rounded-tl-lg")} />
      <span className={cn(corner, "right-0 top-0 border-r-2 border-t-2 rounded-tr-lg")} />
      <span className={cn(corner, "left-0 bottom-0 border-b-2 border-l-2 rounded-bl-lg")} />
      <span className={cn(corner, "right-0 bottom-0 border-b-2 border-r-2 rounded-br-lg")} />
      {active && (
        <span className="pointer-events-none absolute inset-x-8 bottom-0 h-px animate-pulse bg-gradient-to-r from-transparent via-blue-300/60 to-transparent" />
      )}
      {children}
    </div>
  );
}
