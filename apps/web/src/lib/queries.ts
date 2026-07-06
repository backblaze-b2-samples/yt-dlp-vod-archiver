"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  createArchive,
  deleteArchive,
  deleteFile,
  getArchive,
  getArchiveActivity,
  getArchiveAsset,
  getArchives,
  getArchiveStats,
  getFiles,
  getFileStats,
  getPreviewUrl,
  getUploadActivity,
  runArchive,
  updateArchive,
} from "@/lib/api-client";
import type {
  Archive,
  ArchiveConfig,
  FileMetadata,
} from "@yt-dlp-vod-archiver/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  archives: () => [...qk.all, "archives"] as const,
  archive: (id: string) => [...qk.all, "archives", id] as const,
  archiveStats: () => [...qk.all, "archives", "stats"] as const,
  archiveActivity: (days: number) =>
    [...qk.all, "archives", "activity", days] as const,
  asset: (key: string) => [...qk.all, "asset", key] as const,
};

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file). Kept short-lived (60s) because
// the URL itself has a presigned expiry and is cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    // After delete, blow away every cached file list + stats. Cheap and
    // correct — the dashboard re-fetches lazily as components remount.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Archives ---

export function useArchives() {
  return useQuery<Archive[], ApiError>({
    queryKey: qk.archives(),
    queryFn: getArchives,
  });
}

// Poll while a run is in progress so the UI reflects live status/progress.
export function useArchive(id: string | undefined) {
  return useQuery<Archive, ApiError>({
    queryKey: qk.archive(id ?? ""),
    queryFn: () => getArchive(id as string),
    enabled: !!id,
    refetchInterval: (query) =>
      query.state.data?.status === "running" ? 2000 : false,
  });
}

export function useArchiveStats() {
  return useQuery({
    queryKey: qk.archiveStats(),
    queryFn: getArchiveStats,
  });
}

export function useArchiveActivity(days = 7) {
  return useQuery({
    queryKey: qk.archiveActivity(days),
    queryFn: () => getArchiveActivity(days),
  });
}

export function useCreateArchive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (config: ArchiveConfig) => createArchive(config),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}

export function useUpdateArchive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, config }: { id: string; config: ArchiveConfig }) =>
      updateArchive(id, config),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}

export function useDeleteArchive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteArchive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}

export function useRunArchive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => runArchive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}

// Presigned inline URL for an archived asset (clip/VOD). Short staleTime since
// the URL itself has a presigned expiry and is cheap to regenerate.
export function useArchiveAsset(key: string | undefined, enabled = true) {
  return useQuery({
    queryKey: qk.asset(key ?? ""),
    queryFn: () => getArchiveAsset(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}
