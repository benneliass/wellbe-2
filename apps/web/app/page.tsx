import { RootGate } from "@/components/auth/RootGate";

/** Root: the front door. Gated on an explicit session — never auto-entered. */
export default function Home() {
  return <RootGate />;
}
