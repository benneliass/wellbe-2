import { RootGate } from "@/components/auth/RootGate";
import { RootFrame } from "@/components/shell/RootFrame";

/** Root: the front door. Gated on an explicit session — never auto-entered. */
export default function Home() {
  return (
    <RootFrame>
      <RootGate />
    </RootFrame>
  );
}
