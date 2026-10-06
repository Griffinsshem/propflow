"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { maintenanceKeys } from "@/features/maintenance/hooks";
import { photoProblem } from "@/features/maintenance/photos";
import {
  attachmentsApi,
  uploadToStorage,
  type Attachment,
  type PhotoType,
} from "@/lib/api/attachments";

export const attachmentsKey = (orgId: string, requestId: string) =>
  [...maintenanceKeys.detail(orgId, requestId), "attachments"] as const;

export function useAttachments(orgId: string, requestId: string) {
  return useQuery({
    queryKey: attachmentsKey(orgId, requestId),
    queryFn: ({ signal }) => attachmentsApi.list(requestId, signal),
    // Download links are short-lived: refresh them well before they expire.
    staleTime: 60_000,
    refetchInterval: 4 * 60_000,
  });
}

export type UploadState = "uploading" | "processing" | "ready" | "rejected" | "failed";
export type UploadItem = { key: string; name: string; state: UploadState; message: string | null };

const POLL_INTERVAL_MS = 1500;
const MAX_POLLS = 40;

export function usePhotoUploads(orgId: string, requestId: string) {
  const queryClient = useQueryClient();
  const [items, setItems] = useState<UploadItem[]>([]);

  const update = (key: string, patch: Partial<UploadItem>) =>
    setItems((current) => current.map((item) => (item.key === key ? { ...item, ...patch } : item)));

  async function settle(attachment: Attachment): Promise<Attachment> {
    let latest = attachment;
    for (let poll = 0; latest.status !== "ready" && latest.status !== "rejected"; poll += 1) {
      if (poll >= MAX_POLLS) {
        throw new Error("Processing is taking longer than expected. Check back in a few minutes.");
      }
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
      latest = await attachmentsApi.get(requestId, attachment.id);
    }
    return latest;
  }

  async function uploadOne(key: string, file: File): Promise<void> {
    const problem = photoProblem(file);
    if (problem) {
      update(key, { state: "rejected", message: problem });
      return;
    }
    try {
      const { attachment, upload } = await attachmentsApi.start(requestId, {
        content_type: file.type as PhotoType,
        size_bytes: file.size,
      });
      await uploadToStorage(upload, file);
      update(key, { state: "processing" });
      const result = await settle(await attachmentsApi.complete(requestId, attachment.id));
      if (result.status === "ready") {
        update(key, { state: "ready", message: null });
        await queryClient.invalidateQueries({ queryKey: attachmentsKey(orgId, requestId) });
      } else {
        update(key, {
          state: "rejected",
          message: result.rejection_reason ?? "This photo could not be accepted.",
        });
      }
    } catch (error) {
      update(key, {
        state: "failed",
        message: error instanceof Error ? error.message : "The upload failed.",
      });
    }
  }

  function add(files: File[]) {
    const entries = files.map((file) => ({ key: crypto.randomUUID(), file }));
    setItems((current) => [
      ...current,
      ...entries.map(({ key, file }) => ({
        key,
        name: file.name,
        state: "uploading" as const,
        message: null,
      })),
    ]);
    for (const { key, file } of entries) void uploadOne(key, file);
  }

  return { items, add };
}
