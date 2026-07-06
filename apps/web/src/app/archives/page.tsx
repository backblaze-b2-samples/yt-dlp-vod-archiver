import { ArchiveList } from "@/components/archives/archive-list";

export default function ArchivesPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Archives</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
          Register a source URL, then run it to archive the VOD, its metadata,
          and highlight clips to Backblaze B2.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2 space-y-4">
        <ArchiveList />
      </div>
    </div>
  );
}
