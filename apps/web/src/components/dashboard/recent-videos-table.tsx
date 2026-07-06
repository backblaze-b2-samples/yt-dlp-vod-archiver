"use client";

import { useMemo } from "react";
import Link from "next/link";
import { ArrowRight, Inbox } from "lucide-react";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useArchives } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

function humanBytes(size: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let n = size;
  let u = 0;
  while (n >= 1024 && u < units.length - 1) {
    n /= 1024;
    u += 1;
  }
  return `${n.toFixed(1)} ${units[u]}`;
}

export function RecentVideosTable() {
  const { data: archives = [], isLoading, error, refetch } = useArchives();

  const rows = useMemo(() => {
    const flat = archives.flatMap((archive) =>
      archive.videos.map((video) => ({
        archiveId: archive.id,
        title: video.title,
        size: video.size_bytes,
        clips: video.clips.length,
        archivedAt: video.archived_at,
      })),
    );
    flat.sort(
      (a, b) => new Date(b.archivedAt).getTime() - new Date(a.archivedAt).getTime(),
    );
    return flat.slice(0, 10);
  }, [archives]);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Recent Archived Videos</CardTitle>
        <CardAction className="self-center">
          <Link
            href="/archives"
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            View all
            <ArrowRight className="h-3 w-3" />
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : rows.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title="No videos archived yet"
            description="Head to Archives to register and run your first source."
          />
        ) : (
          <Table className="table-fixed">
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="w-[42%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Title
                </TableHead>
                <TableHead className="w-[16%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Size
                </TableHead>
                <TableHead className="w-[14%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Clips
                </TableHead>
                <TableHead className="w-[28%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Archived
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row, i) => (
                <TableRow key={`${row.archiveId}-${i}`} className="table-row-hover">
                  <TableCell className="font-medium">
                    <Link
                      href={`/archives/${row.archiveId}`}
                      className="block truncate hover:underline"
                    >
                      {row.title}
                    </Link>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground tabular-nums whitespace-nowrap">
                    {humanBytes(row.size)}
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap">
                    {row.clips}
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap">
                    {formatDate(row.archivedAt)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
