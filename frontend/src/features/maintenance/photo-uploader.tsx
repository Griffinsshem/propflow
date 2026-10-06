"use client";

import { usePhotoUploads, type UploadState } from "@/features/maintenance/photo-hooks";
import { PHOTO_TYPES } from "@/lib/api/attachments";

const STATE_LABELS: Record<UploadState, string> = {
  uploading: "Uploading…",
  processing: "Processing…",
  ready: "Ready",
  rejected: "Rejected",
  failed: "Failed",
};

const STATE_STYLES: Record<UploadState, string> = {
  uploading: "text-slate-600",
  processing: "text-slate-600",
  ready: "text-green-700",
  rejected: "text-red-600",
  failed: "text-red-600",
};

export function PhotoUploader({ orgId, requestId }: { orgId: string; requestId: string }) {
  const { items, add } = usePhotoUploads(orgId, requestId);

  return (
    <div className="space-y-3">
      <label className="inline-flex cursor-pointer rounded-md bg-white px-3.5 py-2 text-sm font-semibold text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 focus-within:ring-2 focus-within:ring-indigo-600 hover:bg-slate-50">
        Add photos
        <input
          type="file"
          accept={PHOTO_TYPES.join(",")}
          multiple
          className="sr-only"
          onChange={(event) => {
            add(Array.from(event.target.files ?? []));
            event.target.value = ""; // allows choosing the same file again
          }}
        />
      </label>
      <p className="text-sm text-slate-500">
        JPEG, PNG or WebP, up to 10 MB each. Location data is removed before photos are stored.
      </p>
      {items.length > 0 ? (
        <ul aria-label="Photo uploads" aria-live="polite" className="space-y-1 text-sm">
          {items.map((item) => (
            <li key={item.key} className="flex flex-wrap gap-x-2">
              <span className="font-medium text-slate-900">{item.name}</span>
              <span className={STATE_STYLES[item.state]}>
                {STATE_LABELS[item.state]}
                {item.message ? `: ${item.message}` : ""}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
