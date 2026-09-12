import { useUser, useClerk } from "@clerk/clerk-react";
import { Link } from "@tanstack/react-router";
import { Flame, LogOut } from "lucide-react";

export function BrandHeader({ streak = 0 }: { streak?: number }) {
  const { isSignedIn, user } = useUser();
  const { openSignIn, signOut } = useClerk();

  return (
    <header className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 px-4 pt-5 pb-3 md:px-6 md:pt-8">
      <Link to="/" className="flex min-w-0 items-center gap-2">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground">
          <span className="font-display text-lg leading-none">bh</span>
        </span>
        <span className="min-w-0">
          <span className="block truncate font-display text-2xl leading-none tracking-tight md:text-3xl">
            babyoverhattrick
          </span>
          <span className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            cricket trivia, daily
          </span>
        </span>
      </Link>

      <div className="flex shrink-0 items-center gap-2">
        {/* Streak pill — only show when streak > 0 */}
        {streak > 0 && (
          <span className="flex items-center gap-1 rounded-full bg-secondary px-3 py-1.5 text-sm font-bold text-secondary-foreground">
            <Flame className="h-4 w-4 text-accent" aria-hidden="true" />
            {streak}
          </span>
        )}

        {/* Auth */}
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
    </header>
  );
}
