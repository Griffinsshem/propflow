"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { TextAreaField } from "@/components/ui/textarea-field";
import { useChangeStatus } from "@/features/maintenance/status-hooks";
import { actionFor, orderedMoves, reasonProblem } from "@/features/maintenance/workflow";
import { ApiError, messageOf } from "@/lib/api/errors";
import type { MaintenanceRequest, MaintenanceStatus } from "@/lib/api/maintenance";

const CONFLICT_NOTICE =
  "Someone else updated this request just now. It now shows the latest status and the actions available from there.";

export function StatusActions({ orgId, request }: { orgId: string; request: MaintenanceRequest }) {
  const change = useChangeStatus(orgId, request.id);
  const [awaitingReason, setAwaitingReason] = useState<MaintenanceStatus | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const moves = orderedMoves(request.allowed_transitions ?? []);

  async function move(to: MaintenanceStatus, reasonText: string | null) {
    setError(null);
    setNotice(null);
    try {
      await change.mutateAsync({ status: to, reason: reasonText, version: request.version });
      setAwaitingReason(null);
      setReason("");
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 409) {
        setAwaitingReason(null);
        setReason("");
        setNotice(CONFLICT_NOTICE);
        return;
      }
      setError(
        failure instanceof ApiError
          ? (failure.fieldErrors.reason?.[0] ?? failure.message)
          : messageOf(failure),
      );
    }
  }

  function start(to: MaintenanceStatus) {
    setError(null);
    setNotice(null);
    if (actionFor(request.status, to).reasonLabel) {
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
  const pending = awaitingReason ? actionFor(request.status, awaitingReason) : null;

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
            id="status-reason"
            label={pending.reasonLabel ?? "Reason"}
            rows={2}
            value={reason}
            error={error ?? undefined}
            onChange={(event) => setReason(event.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <Button type="submit" pending={change.isPending}>
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
            <div role="group" aria-label="Status actions" className="flex flex-wrap gap-2">
              {moves.map((to) => (
                <Button
                  key={to}
                  type="button"
                  variant={to === "closed" ? "secondary" : "primary"}
                  disabled={change.isPending}
                  pending={change.isPending && change.variables?.status === to}
                  onClick={() => start(to)}
                >
                  {actionFor(request.status, to).label}
                </Button>
              ))}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
