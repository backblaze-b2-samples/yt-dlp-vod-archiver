import { ArchiveDetail } from "@/components/archives/archive-detail";

export default async function ArchiveDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ArchiveDetail id={id} />;
}
