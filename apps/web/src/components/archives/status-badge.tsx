import { Badge } from "@/components/ui/badge";
import type { RunStatus } from "@yt-dlp-vod-archiver/shared";

const VARIANT: Record<
  RunStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  idle: "outline",
  running: "secondary",
  completed: "default",
  failed: "destructive",
};

export function StatusBadge({ status }: { status: RunStatus }) {
  return (
    <Badge variant={VARIANT[status]} className="capitalize">
      {status}
    </Badge>
  );
}
