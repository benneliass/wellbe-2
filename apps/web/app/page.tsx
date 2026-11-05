import { RootGate } from "@/components/auth/RootGate";
import { RootFrame } from "@/components/shell/RootFrame";

/** Root. The guided front door is off unless NEXT_PUBLIC_WELLBE_EXPERIENCE is on. */
export default function Home() {
  return (
    <RootFrame>
      <RootGate />
    </RootFrame>
  );
}
