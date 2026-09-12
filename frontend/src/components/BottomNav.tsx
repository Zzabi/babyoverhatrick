import { Link } from "@tanstack/react-router";
import { Home, Gamepad2, Trophy, UserRound } from "lucide-react";

const items = [
  { to: "/", label: "Home", icon: Home },
  { to: "/games", label: "Games", icon: Gamepad2 },
  { to: "/leaderboard", label: "Leaderboard", icon: Trophy },
  { to: "/signin", label: "Sign in", icon: UserRound },
] as const;

export function BottomNav() {
  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 backdrop-blur md:top-0 md:bottom-auto md:border-t-0 md:border-b"
    >
      <ul className="mx-auto flex max-w-5xl items-stretch justify-between px-2 pb-[env(safe-area-inset-bottom)] md:justify-end md:gap-2 md:px-6">
        {items.map(({ to, label, icon: Icon }) => (
          <li key={to} className="flex-1 md:flex-none">
            <Link
              to={to}
              activeOptions={{ exact: to === "/" }}
              className="flex min-h-[56px] flex-col items-center justify-center gap-1 rounded-lg px-2 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground transition-colors data-[status=active]:text-primary md:flex-row md:gap-2 md:text-sm md:normal-case"
            >
              <Icon className="h-5 w-5" strokeWidth={2.2} aria-hidden="true" />
              {label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
