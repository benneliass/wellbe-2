import { SharedPacketView } from "@/components/prepare/SharedPacketView";

export default async function SharedPacketPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return <SharedPacketView token={token} />;
}
