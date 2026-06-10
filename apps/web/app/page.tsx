import { redirect } from "next/navigation";

/**
 * Root. The Launcher ("front door") lands here in pass 2; for now the app opens
 * directly on the workspace.
 */
export default function Home() {
  redirect("/workspace");
}
