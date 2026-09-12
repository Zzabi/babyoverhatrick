import { SignIn as ClerkSignIn, useUser } from "@clerk/clerk-react";
import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { BrandHeader } from "@/components/BrandHeader";
import { BottomNav } from "@/components/BottomNav";

export const Route = createFileRoute("/signin")({
  component: SignIn,
});

function SignIn() {
  const { isSignedIn } = useUser();

  // If already signed in, just show a "you're in" state
  if (isSignedIn) {
    return (
      <main className="min-h-screen pb-24 md:pt-16">
        <BrandHeader />
        <div className="mx-auto max-w-md px-4 md:px-6 text-center">
          <h1 className="text-3xl leading-tight">You're signed in 🎉</h1>
          <p className="mt-2 text-sm text-muted-foreground">Your streaks and scores are being saved.</p>
          <Link
            to="/"
            className="mt-6 inline-flex min-h-[52px] items-center justify-center rounded-xl bg-primary px-6 font-display text-xl tracking-wide text-primary-foreground"
          >
            Back to games
          </Link>
        </div>
        <BottomNav />
      </main>
    );
  }

  return (
    <main className="min-h-screen pb-24 md:pt-16">
      <BrandHeader />
      <div className="mx-auto max-w-md px-4 md:px-6">
        <h1 className="text-3xl leading-tight">Keep your streak safe</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Playing never needs an account. Signing in just saves your streak, personal bests and rank.
        </p>

        {/* Clerk's hosted sign-in UI — matches your Clerk theme settings */}
        <div className="mt-6">
          <ClerkSignIn
            afterSignInUrl="/"
            afterSignUpUrl="/"
            appearance={{
              elements: {
                rootBox: "w-full",
                card: "shadow-none border border-border rounded-2xl bg-card p-6",
                headerTitle: "font-display text-2xl",
                socialButtonsBlockButton: "min-h-[52px] rounded-xl font-display text-lg tracking-wide tile-press",
                formButtonPrimary: "min-h-[52px] rounded-xl bg-primary font-display text-lg tracking-wide tile-press",
                footerActionText: "text-sm text-muted-foreground",
                footerActionLink: "text-sm font-semibold underline underline-offset-4",
              },
            }}
          />
        </div>

        <Link
          to="/play/guess"
          className="mt-4 block text-center text-sm font-semibold text-muted-foreground underline underline-offset-4"
        >
          Skip — just let me play
        </Link>
      </div>
      <BottomNav />
    </main>
  );
}
