import { LoginScreen } from "@/components/auth/LoginScreen";

export const dynamic = "force-dynamic";

/** ZITADEL login V2 target: /login?authRequest=V2_… (base URI = the web origin). */
export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ authRequest?: string | string[] }>;
}) {
  const { authRequest } = await searchParams;
  const id = typeof authRequest === "string" && /^V2_\d+$/.test(authRequest) ? authRequest : null;
  return (
    <main id="main">
      <LoginScreen authRequestId={id} />
    </main>
  );
}
