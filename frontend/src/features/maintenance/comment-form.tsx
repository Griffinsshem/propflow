"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { TextAreaField } from "@/components/ui/textarea-field";
import { useAddComment } from "@/features/maintenance/activity-hooks";
import { hasControlCharacters } from "@/features/maintenance/schemas";
import { ApiError, messageOf } from "@/lib/api/errors";

const MAX_COMMENT = 5000;

function problemWith(text: string): string | null {
  if (!text) return "Write a comment first.";
  if (text.length > MAX_COMMENT) return `Use at most ${MAX_COMMENT} characters.`;
  if (hasControlCharacters(text)) return "Remove unsupported characters.";
  return null;
}

export function CommentForm({ orgId, requestId }: { orgId: string; requestId: string }) {
  const add = useAddComment(orgId, requestId);
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const text = body.trim();
    const problem = problemWith(text);
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    try {
      await add.mutateAsync(text);
      setBody("");
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 429) {
        setError("You've posted many comments recently. Please try again later.");
      } else if (failure instanceof ApiError) {
        setError(failure.fieldErrors.body?.[0] ?? failure.message);
      } else {
        setError(messageOf(failure));
      }
    }
  }

  return (
    <form onSubmit={submit} noValidate className="space-y-3 border-t border-slate-100 pt-4">
      <TextAreaField
        id="comment-body"
        label="Add a comment"
        rows={3}
        value={body}
        error={error ?? undefined}
        onChange={(event) => setBody(event.target.value)}
      />
      <p className="text-sm text-slate-500">
        Everyone who can see this request can read comments, including the tenant who reported it.
      </p>
      <Button type="submit" variant="secondary" pending={add.isPending}>
        Post comment
      </Button>
    </form>
  );
}
