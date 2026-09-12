import { useSignIn, useSignUp, useClerk } from "@clerk/clerk-react";
import { X } from "lucide-react";
import { useState } from "react";

type Props = {
  open: boolean;
  onDismiss: () => void;
};

/** Soft sign-in prompt. Only rendered after a completed game — never blocks play. */
export function SignInSheet({ open, onDismiss }: Props) {
  const { signIn } = useSignIn();
  const { openSignIn, openSignUp } = useClerk();
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  async function handleGoogle() {
    if (!signIn) return;
    setLoading(true);
    try {
      await signIn.authenticateWithRedirect({
        strategy: "oauth_google",
        redirectUrl: window.location.href,
        redirectUrlComplete: window.location.href,
      });
    } catch {
      setLoading(false);
    }
  }

  function handleEmail() {
    openSignUp({
      afterSignUpUrl: window.location.href,
      afterSignInUrl: window.location.href,
    });
    onDismiss();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-foreground/40 p-0 md:items-center md:p-6">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="signin-title"
        className="w-full max-w-md rounded-t-3xl border border-border bg-card p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] shadow-lg md:rounded-3xl md:pb-5"
      >
        <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
          <h2 id="signin-title" className="min-w-0 font-display text-2xl leading-tight">
            Save that streak?
          </h2>
          <button
            onClick={onDismiss}
            aria-label="Dismiss"
            className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-muted-foreground hover:bg-secondary"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Sign in to keep your streak, rank and personal bests across devices. Takes one tap — you can keep
          playing either way.
        </p>
        <div className="mt-5 grid gap-2">
          <button
            onClick={handleGoogle}
            disabled={loading}
            className="min-h-[52px] rounded-xl bg-primary px-4 font-display text-lg tracking-wide text-primary-foreground tile-press active:tile-press-active disabled:opacity-60"
          >
            {loading ? "Redirecting…" : "Continue with Google"}
          </button>
          <button
            onClick={handleEmail}
            className="min-h-[52px] rounded-xl border border-border bg-secondary px-4 font-display text-lg tracking-wide text-secondary-foreground"
          >
            Use an email instead
          </button>
          <button
            onClick={onDismiss}
            className="min-h-[48px] text-sm font-semibold text-muted-foreground underline underline-offset-4"
          >
            Not now, keep playing
          </button>
        </div>
      </div>
    </div>
  );
}
