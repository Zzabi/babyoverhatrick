import { Link } from "@tanstack/react-router";
import { Home, Gamepad2, Trophy, LogOut } from "lucide-react";
import { useUser, useClerk } from "@clerk/clerk-react";

const navItems = [
  { to: "/", label: "Home", icon: Home },
  { to: "/games", label: "Games", icon: Gamepad2 },
  { to: "/leaderboard", label: "Leaderboard", icon: Trophy },
] as const;

export function BottomNav() {
  const { isSignedIn, user } = useUser();
  const { openSignIn, signOut } = useClerk();

  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 backdrop-blur md:top-0 md:bottom-auto md:border-t-0 md:border-b"
    >
      <div className="mx-auto flex max-w-5xl items-stretch px-2 pb-[env(safe-area-inset-bottom)] md:px-6 md:pb-0">

        {/* Logo — desktop top bar only */}
        <Link to="/" className="hidden md:flex shrink-0 items-center gap-2 mr-6 py-3">
          <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground">
            <span className="font-display text-base leading-none">bh</span>
          </span>
          <span className="font-display text-xl leading-none tracking-tight">babyoverhattrick</span>
        </Link>

        {/* Nav items */}
        <ul className="flex flex-1 items-stretch justify-between md:justify-start md:gap-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <li key={to} className="flex-1 md:flex-none">
              <Link
                to={to}
                activeOptions={{ exact: to === "/" }}
                className="flex min-h-[56px] flex-col items-center justify-center gap-1 rounded-lg px-2 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground transition-colors data-[status=active]:text-primary md:flex-row md:gap-2 md:min-h-0 md:py-3 md:px-3 md:text-sm md:normal-case"
              >
                <Icon className="h-5 w-5" strokeWidth={2.2} aria-hidden="true" />
                {label}
              </Link>
            </li>
          ))}
        </ul>

        {/* Auth — desktop top bar only */}
        <div className="hidden md:flex items-center ml-auto pl-4">
          {isSignedIn ? (
            <div className="flex items-center gap-2">
              {user.imageUrl ? (
                <img
                  src={user.imageUrl}
                  alt={user.fullName ?? "Profile"}
                  className="h-8 w-8 rounded-full object-cover border border-border"
                />
              ) : (
                <span className="grid h-8 w-8 place-items-center rounded-full bg-accent text-accent-foreground font-bold text-sm">
                  {(user.firstName?.[0] ?? user.emailAddresses[0]?.emailAddress[0] ?? "U").toUpperCase()}
                </span>
              )}
              <button
                onClick={() => signOut({ redirectUrl: "/" })}
                aria-label="Sign out"
                className="grid h-8 w-8 place-items-center rounded-full text-muted-foreground hover:bg-secondary"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => openSignIn({ afterSignInUrl: window.location.href })}
              className="rounded-full bg-secondary px-3 py-1.5 text-sm font-bold text-secondary-foreground hover:bg-secondary/80"
            >
              Sign in
            </button>
          )}
        </div>

      </div>
    </nav>
  );
}
