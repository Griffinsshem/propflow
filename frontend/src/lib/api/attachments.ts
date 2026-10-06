import { apiRequest } from "./client";

export const PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"] as const;
export const MAX_PHOTO_BYTES = 10 * 1024 * 1024;

export type PhotoType = (typeof PHOTO_TYPES)[number];
export type AttachmentStatus = "pending" | "processing" | "ready" | "rejected";

export type Attachment = {
  id: string;
  status: AttachmentStatus;
  content_type: string;
  size_bytes: number | null;
  width: number | null;
  height: number | null;
  rejection_reason: string | null;
  uploaded_by_membership_id: string;
  created_at: string;
  ready_at: string | null;
  download_url: string | null;
};

export type UploadInstructions = {
  method: string;
  url: string;
  headers: Record<string, string>;
  expires_in: number;
};

const enc = encodeURIComponent;
const base = (requestId: string) => `/maintenance/${enc(requestId)}/attachments`;

export const attachmentsApi = {
  list: (requestId: string, signal?: AbortSignal) =>
    apiRequest<Attachment[]>(base(requestId), { signal }),
  get: (requestId: string, id: string) => apiRequest<Attachment>(`${base(requestId)}/${enc(id)}`),
  start: (requestId: string, body: { content_type: PhotoType; size_bytes: number }) =>
    apiRequest<{ attachment: Attachment; upload: UploadInstructions }>(base(requestId), {
      method: "POST",
      body,
    }),
  complete: (requestId: string, id: string) =>
    apiRequest<Attachment>(`${base(requestId)}/${enc(id)}/complete`, { method: "POST" }),
};

/** Sends the file straight to storage. The signed URL is the only credential: no cookies. */
export async function uploadToStorage(upload: UploadInstructions, file: Blob): Promise<void> {
  let response: Response;
  try {
    response = await fetch(upload.url, {
      method: upload.method,
      headers: upload.headers,
      body: file,
      credentials: "omit",
    });
  } catch {
    throw new Error("The photo could not be uploaded. Check your connection and try again.");
  }
  if (!response.ok) throw new Error("The photo could not be uploaded. Please try again.");
}
