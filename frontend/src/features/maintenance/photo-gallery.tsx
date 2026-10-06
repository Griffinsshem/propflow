"use client";

import { FormAlert } from "@/components/ui/form-alert";
import { useAttachments } from "@/features/maintenance/photo-hooks";
import { messageOf } from "@/lib/api/errors";

export function PhotoGallery({ orgId, requestId }: { orgId: string; requestId: string }) {
  const photos = useAttachments(orgId, requestId);
  if (photos.isPending) return <p className="text-sm text-slate-500">Loading photos…</p>;
  if (photos.isError) return <FormAlert>{messageOf(photos.error)}</FormAlert>;
  const ready = photos.data.filter((photo) => photo.download_url);
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
