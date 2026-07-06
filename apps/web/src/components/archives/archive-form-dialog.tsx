"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { ApiError } from "@/lib/api-client";
import { useCreateArchive, useUpdateArchive } from "@/lib/queries";
import type { Archive } from "@yt-dlp-vod-archiver/shared";

const DEMO_URL =
  "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4";

const CLIP_MODES = ["interval", "chapters", "none"] as const;
const CLIP_LENGTHS = ["5", "15", "30", "60"] as const;
const MAX_CLIPS = ["1", "3", "5", "10"] as const;

const schema = z.object({
  url: z.string().url("Enter a valid http(s) URL"),
  title: z.string().max(120, "Title must be 120 characters or fewer").optional(),
  clip_mode: z.enum(CLIP_MODES),
  clip_length_seconds: z.enum(CLIP_LENGTHS),
  max_clips: z.enum(MAX_CLIPS),
});

type FormValues = z.infer<typeof schema>;

const CREATE_DEFAULTS: FormValues = {
  url: "",
  title: "",
  clip_mode: "interval",
  clip_length_seconds: "5",
  max_clips: "3",
};

function asPreset<T extends readonly string[]>(
  options: T,
  value: number,
  fallback: T[number],
): T[number] {
  const s = String(value);
  return (options as readonly string[]).includes(s) ? (s as T[number]) : fallback;
}

interface ArchiveFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "edit";
  archive?: Archive;
}

export function ArchiveFormDialog({
  open,
  onOpenChange,
  mode,
  archive,
}: ArchiveFormDialogProps) {
  const createMutation = useCreateArchive();
  const updateMutation = useUpdateArchive();
  const isEdit = mode === "edit";

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: CREATE_DEFAULTS,
  });

  // Sync form values whenever the dialog opens (prefill for edit, reset for create).
  useEffect(() => {
    if (!open) return;
    if (isEdit && archive) {
      form.reset({
        url: archive.url,
        title: archive.title,
        clip_mode: archive.clip_mode,
        clip_length_seconds: asPreset(CLIP_LENGTHS, archive.clip_length_seconds, "5"),
        max_clips: asPreset(MAX_CLIPS, archive.max_clips, "3"),
      });
    } else {
      form.reset(CREATE_DEFAULTS);
    }
  }, [open, isEdit, archive, form]);

  const onSubmit = async (values: FormValues) => {
    const config = {
      url: values.url,
      title: values.title ?? "",
      clip_mode: values.clip_mode,
      clip_length_seconds: Number(values.clip_length_seconds),
      max_clips: Number(values.max_clips),
    };
    try {
      if (isEdit && archive) {
        await updateMutation.mutateAsync({ id: archive.id, config });
        toast.success("Archive updated");
      } else {
        const created = await createMutation.mutateAsync(config);
        toast.success(`Archive "${created.title}" created`);
      }
      onOpenChange(false);
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.message : "Failed to save archive";
      toast.error(detail);
    }
  };

  const submitting = createMutation.isPending || updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit archive" : "New archive"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Update this source's title and clip settings."
              : "Register a source URL to archive to Backblaze B2."}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
            <FormField
              control={form.control}
              name="url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Source URL</FormLabel>
                  <FormControl>
                    <Input placeholder="https://…" {...field} />
                  </FormControl>
                  {!isEdit && (
                    <FormDescription className="break-all">
                      Try a small, reliably-fetchable demo source, e.g.{" "}
                      {DEMO_URL}
                    </FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Title</FormLabel>
                  <FormControl>
                    <Input placeholder="Big Buck Bunny" {...field} />
                  </FormControl>
                  <FormDescription>
                    Optional — derived from the URL if left blank.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="clip_mode"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Clip mode</FormLabel>
                  <FormControl>
                    <RadioGroup
                      onValueChange={field.onChange}
                      value={field.value}
                      className="flex gap-6"
                    >
                      {CLIP_MODES.map((m) => (
                        <label
                          key={m}
                          className="flex items-center gap-2 text-sm capitalize cursor-pointer"
                        >
                          <RadioGroupItem value={m} />
                          {m}
                        </label>
                      ))}
                    </RadioGroup>
                  </FormControl>
                  {!isEdit && (
                    <FormDescription>
                      interval works on any video (recommended).
                    </FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="clip_length_seconds"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Clip length (s)</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {CLIP_LENGTHS.map((s) => (
                          <SelectItem key={s} value={s}>
                            {s}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {!isEdit && <FormDescription>5 recommended.</FormDescription>}
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="max_clips"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Max clips</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {MAX_CLIPS.map((n) => (
                          <SelectItem key={n} value={n}>
                            {n}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {!isEdit && <FormDescription>3 recommended.</FormDescription>}
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting
                  ? "Saving…"
                  : isEdit
                    ? "Save changes"
                    : "Create archive"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
