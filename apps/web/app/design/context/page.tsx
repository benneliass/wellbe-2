import { redirect } from "next/navigation";

/** Compatibility entry: context is a view of the graph workspace. */
export default function ContextDesignPage() { redirect("/design/graph?view=context"); }
