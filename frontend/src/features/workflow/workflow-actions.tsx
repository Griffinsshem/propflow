"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { TextAreaField } from "@/components/ui/textarea-field";
import { reasonProblem } from "@/features/maintenance/workflow";
import { ApiError, messageOf } from "@/lib/api/errors";

export type MoveDescription = { label: string; reasonLabel: string | null };

type WorkflowActionsProps<S extends string> = {
  /** Accessible name of the button group, e.g. "Status actions". */
  groupLabel: string;
  /** The moves the API allows this user right now (allowed_transitions), in display order. */
  moves: readonly S[];
  describe: (to: S) => MoveDescription;
  isSecondary?: (to: S) => boolean;
  onMove: (to: S, reason: string | null) => Promise<unknown>;
  busy: boolean;
  pendingMove: S | null;
  /** Shown when the record changed underneath this user (409): the caller refreshes it. */
  conflictNotice: string;
};

export function WorkflowActions<S extends string>({
  groupLabel,
  moves,
  describe,
  isSecondary = () => false,
  onMove,
  busy,
  pendingMove,
  conflictNotice,
}: WorkflowActionsProps<S>) {
  const [awaitingReason, setAwaitingReason] = useState<S | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function move(to: S, reasonText: string | null) {
    setError(null);
    setNotice(null);
    try {
      await onMove(to, reasonText);
      setAwaitingReason(null);
      setReason("");
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 409) {
        setAwaitingReason(null);
        setReason("");
        setNotice(conflictNotice);
        return;
      }
      setError(
        failure instanceof ApiError
          ? (failure.fieldErrors.reason?.[0] ?? failure.message)
          : messageOf(failure),
      );
    }
  }

  function start(to: S) {
    setError(null);
    setNotice(null);
    if (describe(to).reasonLabel) {
      setAwaitingReason(to);
      setReason("");
    } else {
      void move(to, null);
    }
  }

  function confirm(event: FormEvent) {
    event.preventDefault();
    if (!awaitingReason) return;
    const text = reason.trim();
    const problem = reasonProblem(text);
    if (problem) {
      setError(problem);
      return;
    }
    void move(awaitingReason, text);
  }

  if (moves.length === 0 && !notice) return null;
  const pending = awaitingReason ? describe(awaitingReason) : null;

  return (
    <div className="space-y-3">
      {notice ? (
        <p
          role="status"
          className="rounded-md bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-amber-200"
        >
          {notice}
        </p>
      ) : null}
      {awaitingReason && pending ? (
        <form
          onSubmit={confirm}
          noValidate
          className="space-y-3 rounded-md bg-slate-50 p-4 ring-1 ring-slate-200"
        >
          <TextAreaField
            id="workflow-reason"
            label={pending.reasonLabel ?? "Reason"}
            rows={2}
            value={reason}
            error={error ?? undefined}
            onChange={(event) => setReason(event.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <Button type="submit" pending={busy}>
              {pending.label}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setAwaitingReason(null);
                setError(null);
              }}
            >
              Cancel
            </Button>
          </div>
        </form>
      ) : (
        <>
          {error ? <FormAlert>{error}</FormAlert> : null}
          {moves.length > 0 ? (
            <div role="group" aria-label={groupLabel} className="flex flex-wrap gap-2">
              {moves.map((to) => (
                <Button
                  key={to}
                  type="button"
                  variant={isSecondary(to) ? "secondary" : "primary"}
                  disabled={busy}
                  pending={busy && pendingMove === to}
                  onClick={() => start(to)}
                >
                  {describe(to).label}
                </Button>
              ))}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
