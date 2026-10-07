"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/text-field";
import { useInviteContractorLogin } from "@/features/contractors/hooks";
import { tenantEmailSchema } from "@/features/tenants/schemas";
import type { Contractor } from "@/lib/api/contractors";
import { ApiError, messageOf } from "@/lib/api/errors";

export function ContractorLoginSection({
  orgId,
  contractor,
}: {
  orgId: string;
  contractor: Contractor;
}) {
  const invite = useInviteContractorLogin(orgId);
  const [email, setEmail] = useState(contractor.email ?? "");
  const [error, setError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);

  if (contractor.has_login) {
    return (
      <p className="text-sm text-slate-700">
        This contractor can sign in. Work orders assigned to them appear on their dashboard.
      </p>
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSentTo(null);
    const parsed = tenantEmailSchema.safeParse(email);
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Enter a valid email address.");
      return;
    }
    setError(null);
    try {
      await invite.mutateAsync({ id: contractor.id, email: parsed.data });
      setSentTo(parsed.data);
    } catch (failure) {
      setError(
        failure instanceof ApiError
          ? (failure.fieldErrors.email?.[0] ?? failure.message)
          : messageOf(failure),
      );
    }
  }

  return (
    <form onSubmit={submit} noValidate className="space-y-3">
      <p className="text-sm text-slate-600">
        This contractor can&apos;t sign in yet. Invite the person who will handle their jobs:
        accepting the invitation links their login to this contractor.
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <TextField
          id="contractor-login-email"
          label="Login email"
          type="email"
          autoComplete="off"
          className="min-w-56 flex-1"
          value={email}
          error={error ?? undefined}
          onChange={(event) => setEmail(event.target.value)}
        />
        <Button type="submit" variant="secondary" pending={invite.isPending}>
          Invite to sign in
        </Button>
      </div>
      <p role="status" className="text-sm text-green-700">
        {sentTo ? `Invitation sent to ${sentTo}.` : ""}
      </p>
    </form>
  );
}
