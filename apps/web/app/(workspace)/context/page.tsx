import { redirect } from "next/navigation";

/** Old record-map links open the context view in the single graph workspace. */
export default async function ContextPage({ searchParams }: { searchParams: Promise<{ preview?: string }> }) {
  const { preview } = await searchParams;
  redirect(`/graph?view=context${preview === "design" ? "&preview=design" : ""}`);
}
