"use client";

import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { ApiError } from "@/lib/api-client";
import { useDeleteArchive } from "@/lib/queries";
import type { Archive } from "@yt-dlp-vod-archiver/shared";

interface DeleteArchiveDialogProps {
  archive: Archive | null;
  onOpenChange: (open: boolean) => void;
  onDeleted?: () => void;
}

export function DeleteArchiveDialog({
  archive,
  onOpenChange,
  onDeleted,
}: DeleteArchiveDialogProps) {
  const deleteMutation = useDeleteArchive();

  const confirmDelete = () => {
    if (!archive) return;
    const target = archive;
    deleteMutation.mutate(target.id, {
      onSuccess: () => {
        toast.success(`Archive "${target.title}" deleted`);
        onDeleted?.();
      },
      onError: (err) => {
        const detail =
          err instanceof ApiError ? err.message : "Failed to delete archive";
        toast.error(detail);
      },
      onSettled: () => onOpenChange(false),
    });
  };

  return (
    <AlertDialog
      open={!!archive}
      onOpenChange={(open) => !open && onOpenChange(false)}
    >
      <AlertDialogContent className="max-w-[calc(100vw-2rem)] sm:max-w-lg">
        <AlertDialogHeader>
          <AlertDialogTitle>Delete archive?</AlertDialogTitle>
          <AlertDialogDescription className="break-words">
            This permanently deletes{" "}
            <strong className="break-all font-semibold text-foreground">
              {archive?.title}
            </strong>{" "}
            — its VOD, metadata, and clips under{" "}
            <code className="text-xs">archive/…/{archive?.id}/</code> in B2, plus
            its manifest entry. This action cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleteMutation.isPending}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={confirmDelete}
            disabled={deleteMutation.isPending}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {deleteMutation.isPending ? "Deleting…" : "Delete"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
