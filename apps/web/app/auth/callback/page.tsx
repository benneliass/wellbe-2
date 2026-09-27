import { AuthCallback } from "@/components/auth/AuthCallback";

/** OIDC redirect target (redirect URI = <origin>/auth/callback). */
export default function AuthCallbackPage() {
  return (
    <main id="main">
      <AuthCallback />
    </main>
  );
}
