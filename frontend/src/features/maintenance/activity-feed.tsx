"use client";

import { FormAlert } from "@/components/ui/form-alert";
import { describeStatusChange, mergeActivity } from "@/features/maintenance/activity";
import { useComments, useHistory } from "@/features/maintenance/activity-hooks";
import { messageOf } from "@/lib/api/errors";
import { formatDateTime } from "@/lib/format";

function When({ at }: { at: string }) {
  return (
    <time dateTime={at} className="text-xs text-slate-500">
      {formatDateTime(at)}
    </time>
  );
}

export function ActivityFeed({ orgId, requestId }: { orgId: string; requestId: string }) {
  const history = useHistory(orgId, requestId);
  const comments = useComments(orgId, requestId);

  if (history.isPending || comments.isPending) {
    return <p className="text-sm text-slate-500">Loading activity…</p>;
  }
  if (history.isError) return <FormAlert>{messageOf(history.error)}</FormAlert>;
  if (comments.isError) return <FormAlert>{messageOf(comments.error)}</FormAlert>;

  const items = mergeActivity(history.data, comments.data.items);
  return (
    <div className="space-y-3">
      {comments.data.next_cursor ? (
        <p className="text-sm text-slate-500">Showing the latest 100 comments.</p>
      ) : null}
      <ol aria-label="Activity" className="space-y-3">
        {items.map((item) =>
          item.kind === "status" ? (
            <li key={item.key} className="flex gap-3 text-sm">
              <span aria-hidden className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-slate-400" />
              <div>
                <p className="text-slate-700">{describeStatusChange(item.entry)}</p>
                {item.entry.reason ? (
                  <p className="text-slate-600">Reason: {item.entry.reason}</p>
                ) : null}
                <When at={item.at} />
              </div>
            </li>
          ) : (
            <li key={item.key} className="rounded-md bg-slate-50 p-3 text-sm ring-1 ring-slate-200">
              <p className="font-medium text-slate-900">{item.comment.author.full_name}</p>
              {/* Plain text, rendered as text: comments can never become markup. */}
              <p className="mt-1 whitespace-pre-wrap text-slate-700">{item.comment.body}</p>
              <When at={item.at} />
            </li>
          ),
        )}
      </ol>
    </div>
  );
}
