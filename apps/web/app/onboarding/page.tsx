import { OnboardingFlow } from "@/components/auth/OnboardingFlow";

/** First-run onboarding: welcome, core consent, minimal baseline, confirm.
 * Shown unless NEXT_PUBLIC_WELLBE_EXPERIENCE is off. */
export default function OnboardingPage() {
  return (
    <main id="main">
      <OnboardingFlow />
    </main>
  );
}
