"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Eye, Film, Pencil, Play, Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { ApiError } from "@/lib/api-client";
import { useArchives, useRunArchive } from "@/lib/queries";
import { ArchiveFormDialog } from "./archive-form-dialog";
import { DeleteArchiveDialog } from "./delete-archive-dialog";
import { StatusBadge } from "./status-badge";
import type { Archive } from "@yt-dlp-vod-archiver/shared";

export function ArchiveList() {
  const { data: archives = [], isLoading, error, refetch } = useArchives();
  const runMutation = useRunArchive();

  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Archive | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Archive | null>(null);

  const handleRun = (archive: Archive) => {
    runMutation.mutate(archive.id, {
      onSuccess: () => toast.success(`Run started for "${archive.title}"`),
      onError: (err) => {
        const detail =
          err instanceof ApiError ? err.message : "Failed to start run";
        toast.error(detail);
      },
    });
  };

  return (
    <>
      <div className="flex justify-end">
        <Button size="sm" className="h-8" onClick={() => setCreateOpen(true)}>
          <Plus className="h-3.5 w-3.5" />
          New archive
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : error ? (
        <Card>
          <CardContent className="p-0">
            <ErrorState
              error={error}
              title="Couldn't load archives"
              onRetry={() => refetch()}
            />
          </CardContent>
        </Card>
      ) : archives.length === 0 ? (
        <Card>
          <CardContent className="p-0">
            <EmptyState
              icon={Film}
              title="No archives yet"
              description="Register a source URL to start archiving VODs to B2."
              action={
                <Button size="sm" onClick={() => setCreateOpen(true)}>
                  <Plus className="h-3.5 w-3.5" />
                  New archive
                </Button>
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {archives.map((archive) => (
            <Card key={archive.id} className="card-hover">
              <CardContent className="flex flex-wrap items-center justify-between gap-4 p-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <Link
                      href={`/archives/${archive.id}`}
                      className="font-semibold truncate hover:underline"
                    >
                      {archive.title}
                    </Link>
                    <StatusBadge status={archive.status} />
                  </div>
                  <p className="mt-1 truncate text-xs text-muted-foreground">
                    {archive.url}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {archive.videos.length} video
                    {archive.videos.length === 1 ? "" : "s"} · {archive.clip_mode}
                  </p>
                  {archive.status === "running" && (
                    <div className="mt-2 max-w-sm">
                      <Progress value={archive.progress} className="h-1.5" />
                      <p className="mt-1 text-xs text-muted-foreground">
                        {archive.current_step}
                      </p>
                    </div>
                  )}
                  {archive.status === "failed" && archive.last_error && (
                    <p className="mt-1 text-xs text-destructive truncate">
                      {archive.last_error}
                    </p>
                  )}
                </div>

                <div className="flex shrink-0 items-center gap-1.5">
                  <Button
                    size="sm"
                    variant="default"
                    className="h-8"
                    disabled={archive.status === "running"}
                    onClick={() => handleRun(archive)}
                  >
                    <Play className="h-3.5 w-3.5" />
                    Run
                  </Button>
                  <Button asChild size="sm" variant="outline" className="h-8">
                    <Link href={`/archives/${archive.id}`}>
                      <Eye className="h-3.5 w-3.5" />
                      View
                    </Link>
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8"
                    aria-label="Edit archive"
                    onClick={() => setEditTarget(archive)}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8 text-destructive hover:text-destructive"
                    aria-label="Delete archive"
                    onClick={() => setDeleteTarget(archive)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <ArchiveFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        mode="create"
      />
      <ArchiveFormDialog
        open={!!editTarget}
        onOpenChange={(open) => !open && setEditTarget(null)}
        mode="edit"
        archive={editTarget ?? undefined}
      />
      <DeleteArchiveDialog
        archive={deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
      />
    </>
  );
}
