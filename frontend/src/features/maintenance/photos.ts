import { MAX_PHOTO_BYTES, PHOTO_TYPES } from "@/lib/api/attachments";

/** Checked before uploading; the API checks again, and the worker inspects the actual bytes. */
export function photoProblem(file: { type: string; size: number }): string | null {
  if (!(PHOTO_TYPES as readonly string[]).includes(file.type)) {
    return "Only JPEG, PNG or WebP photos can be added.";
  }
  if (file.size === 0) return "This file is empty.";
  if (file.size > MAX_PHOTO_BYTES) return "Photos must be 10 MB or smaller.";
  return null;
}
