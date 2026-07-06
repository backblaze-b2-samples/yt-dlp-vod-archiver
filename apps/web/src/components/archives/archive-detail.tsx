"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  AlertTriangle,
  ArrowLeft,
  Download,
  Film,
  Pencil,
  Play,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { ApiError, getArchiveAsset } from "@/lib/api-client";
import { useArchive, useArchiveAsset, useRunArchive } from "@/lib/queries";
import { ArchiveFormDialog } from "./archive-form-dialog";
import { DeleteArchiveDialog } from "./delete-archive-dialog";
import { StatusBadge } from "./status-badge";
import type { ArchivedVideo, Clip } from "@yt-dlp-vod-archiver/shared";

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

async function downloadAsset(key: string) {
  try {
    const { url } = await getArchiveAsset(key, true);
    window.open(url, "_blank");
  } catch (err) {
    toast.error(err instanceof ApiError ? err.message : "Failed to get download URL");
  }
}

function ClipCard({ clip }: { clip: Clip }) {
  const { data, isLoading, error } = useArchiveAsset(clip.key);
  return (
    <div className="rounded-md border border-border p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-sm font-medium">{clip.label}</span>
        <span className="font-mono text-xs text-muted-foreground tabular-nums">
          {clip.start.toFixed(1)}s–{clip.end.toFixed(1)}s
        </span>
      </div>
      {isLoading ? (
        <Skeleton className="aspect-video w-full" />
      ) : error || !data ? (
        <p className="text-xs text-destructive">Couldn&apos;t load clip preview.</p>
      ) : (
        <video
          controls
          preload="metadata"
          src={data.url}
          className="aspect-video w-full rounded bg-black"
        />
      )}
      <Button
        variant="ghost"
        size="sm"
        className="mt-2 h-7 text-xs"
        onClick={() => downloadAsset(clip.key)}
      >
        <Download className="h-3 w-3" />
        Download
      </Button>
    </div>
  );
}

function VideoRow({ video }: { video: ArchivedVideo }) {
  return (
    <AccordionItem value={video.video_id}>
      <AccordionTrigger className="px-1">
        <div className="flex min-w-0 flex-1 items-center gap-3 pr-3">
          <Film className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="truncate font-medium">{video.title}</span>
          <span className="ml-auto shrink-0 text-xs text-muted-foreground">
            {video.clips.length} clip{video.clips.length === 1 ? "" : "s"} ·{" "}
            {humanBytes(video.size_bytes)}
          </span>
        </div>
      </AccordionTrigger>
      <AccordionContent className="px-1">
        {video.clip_strategy === "chapters_fallback_interval" && (
          <p className="mb-3 flex items-start gap-1.5 text-xs text-muted-foreground">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              Chapters mode was requested, but this source has no chapter
              markers — fell back to evenly-spaced interval clips.
            </span>
          </p>
        )}
        <div className="mb-3 grid grid-cols-2 gap-2 text-xs text-muted-foreground sm:grid-cols-4">
          <div>
            <div className="font-semibold text-foreground">Duration</div>
            {Math.round(video.duration_seconds)}s
          </div>
          <div>
            <div className="font-semibold text-foreground">Size</div>
            {humanBytes(video.size_bytes)}
          </div>
          <div className="col-span-2 min-w-0">
            <div className="font-semibold text-foreground">VOD key</div>
            <code className="block truncate">{video.vod_key}</code>
          </div>
        </div>
        <div className="mb-3 flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={() => downloadAsset(video.vod_key)}
          >
            <Download className="h-3 w-3" />
            Download VOD
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={() => downloadAsset(video.meta_key)}
          >
            <Download className="h-3 w-3" />
            Metadata JSON
          </Button>
        </div>
        {video.clips.length === 0 ? (
          <p className="text-xs text-muted-foreground">
            No clips were cut for this video.
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {video.clips.map((clip) => (
              <ClipCard key={clip.key} clip={clip} />
            ))}
          </div>
        )}
      </AccordionContent>
    </AccordionItem>
  );
}

export function ArchiveDetail({ id }: { id: string }) {
  const router = useRouter();
  const { data: archive, isLoading, error, refetch } = useArchive(id);
  const runMutation = useRunArchive();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }
  if (error || !archive) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState
            error={error ?? new ApiError("Archive not found", 404)}
            title="Couldn't load archive"
            onRetry={() => refetch()}
          />
        </CardContent>
      </Card>
    );
  }

  const handleRun = () => {
    runMutation.mutate(archive.id, {
      onSuccess: () => toast.success("Run started"),
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "Failed to start run"),
    });
  };

  return (
    <div className="space-y-6">
      <Button
        variant="ghost"
        size="sm"
        className="h-7 px-2 text-xs"
        onClick={() => router.push("/archives")}
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        All archives
      </Button>

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <CardTitle className="card-title truncate">{archive.title}</CardTitle>
              <StatusBadge status={archive.status} />
            </div>
            <a
              href={archive.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 block truncate text-xs text-muted-foreground hover:text-foreground"
            >
              {archive.url}
            </a>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <Button
              size="sm"
              className="h-8"
              disabled={archive.status === "running"}
              onClick={handleRun}
            >
              <Play className="h-3.5 w-3.5" />
              Run
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8"
              aria-label="Edit archive"
              onClick={() => setEditOpen(true)}
            >
              <Pencil className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8 text-destructive hover:text-destructive"
              aria-label="Delete archive"
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="px-5 py-4">
          {archive.status === "running" ? (
            <div className="max-w-md space-y-1">
              <Progress value={archive.progress} className="h-2" />
              <p className="text-xs text-muted-foreground">
                {archive.current_step} · {archive.progress}%
              </p>
            </div>
          ) : archive.status === "failed" && archive.last_error ? (
            <p className="text-sm text-destructive">{archive.last_error}</p>
          ) : (
            <p className="text-xs text-muted-foreground">
              {archive.clip_mode} · {archive.clip_length_seconds}s clips · up to{" "}
              {archive.max_clips}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b border-border px-5 py-4">
          <CardTitle className="card-title">
            Archived videos ({archive.videos.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-3">
          {archive.videos.length === 0 ? (
            <EmptyState
              icon={Film}
              title="Nothing archived yet"
              description="Run this archive to download the VOD, capture metadata, and cut clips."
            />
          ) : (
            <Accordion type="multiple" className="w-full">
              {archive.videos.map((video) => (
                <VideoRow key={video.video_id} video={video} />
              ))}
            </Accordion>
          )}
        </CardContent>
      </Card>

      <ArchiveFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        mode="edit"
        archive={archive}
      />
      <DeleteArchiveDialog
        archive={deleteOpen ? archive : null}
        onOpenChange={(open) => !open && setDeleteOpen(false)}
        onDeleted={() => router.push("/archives")}
      />
    </div>
  );
}
