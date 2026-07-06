export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- VOD archive pipeline ---

export type ClipMode = "chapters" | "interval" | "none";
export type RunStatus = "idle" | "running" | "completed" | "failed";

export interface Clip {
  key: string;
  start: number;
  end: number;
  label: string;
}

export interface ArchivedVideo {
  video_id: string;
  title: string;
  duration_seconds: number;
  vod_key: string;
  meta_key: string;
  size_bytes: number;
  thumbnail_url: string | null;
  archived_at: string;
  clips: Clip[];
}

/** Create/edit payload for an archive. */
export interface ArchiveConfig {
  url: string;
  title?: string;
  clip_mode: ClipMode;
  clip_length_seconds: number;
  max_clips: number;
}

export interface Archive {
  id: string;
  title: string;
  url: string;
  clip_mode: ClipMode;
  clip_length_seconds: number;
  max_clips: number;
  status: RunStatus;
  progress: number;
  current_step: string;
  last_error: string | null;
  created_at: string;
  last_run_at: string | null;
  videos: ArchivedVideo[];
}

export interface ArchiveManifest {
  archives: Archive[];
  updated_at: string | null;
}

export interface ArchiveStats {
  total_archives: number;
  total_videos: number;
  total_clips: number;
  total_size_bytes: number;
  total_size_human: string;
}

export interface DailyArchiveCount {
  date: string;
  videos: number;
}
