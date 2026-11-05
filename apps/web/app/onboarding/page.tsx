import { OnboardingFlow } from "@/components/auth/OnboardingFlow";

/** First-run onboarding: welcome, core consent, minimal baseline, confirm.
 * Hidden while the guided experience is off. Set NEXT_PUBLIC_WELLBE_EXPERIENCE=on to show it. */
export default function OnboardingPage() {
  return (
    <main id="main">
      <OnboardingFlow />
    </main>
  );
}
