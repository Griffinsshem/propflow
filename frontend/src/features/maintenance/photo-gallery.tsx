"use client";

import { FormAlert } from "@/components/ui/form-alert";
import { useAttachments } from "@/features/maintenance/photo-hooks";
import type { Attachment } from "@/lib/api/attachments";
import { messageOf } from "@/lib/api/errors";

/** Ready photos as a grid; used wherever someone is allowed to see them. */
export function PhotoGrid({ photos }: { photos: Attachment[] }) {
  const ready = photos.filter((photo) => photo.download_url);
  if (ready.length === 0) return <p className="text-sm text-slate-500">No photos yet.</p>;
  return (
    <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {ready.map((photo, index) => (
        <li key={photo.id}>
          <a href={photo.download_url ?? undefined} target="_blank" rel="noopener noreferrer">
            {/* Short-lived signed URLs: Next's image optimizer must not fetch or cache them. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={photo.download_url ?? undefined}
              alt={`Photo ${index + 1}`}
              loading="lazy"
              className="aspect-square w-full rounded-md object-cover ring-1 ring-slate-200"
            />
          </a>
        </li>
      ))}
    </ul>
  );
}

export function PhotoGallery({ orgId, requestId }: { orgId: string; requestId: string }) {
  const photos = useAttachments(orgId, requestId);
  if (photos.isPending) return <p className="text-sm text-slate-500">Loading photos…</p>;
  if (photos.isError) return <FormAlert>{messageOf(photos.error)}</FormAlert>;
  return <PhotoGrid photos={photos.data} />;
}
