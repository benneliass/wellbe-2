import { RootGate } from "@/components/auth/RootGate";
import { RootFrame } from "@/components/shell/RootFrame";

/** Root. The front door is on unless NEXT_PUBLIC_WELLBE_EXPERIENCE is off. */
export default function Home() {
  return (
    <RootFrame>
      <RootGate />
    </RootFrame>
  );
}
