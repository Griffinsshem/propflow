"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/text-field";
import { useInviteTenant } from "@/features/tenants/hooks";
import { tenantEmailSchema } from "@/features/tenants/schemas";
import { ApiError, messageOf } from "@/lib/api/errors";

export function InviteTenantForm({ orgId, unitId }: { orgId: string; unitId: string }) {
  const invite = useInviteTenant(orgId);
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);

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
      await invite.mutateAsync({ email: parsed.data, unitId });
      setSentTo(parsed.data);
      setEmail("");
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
        This unit has no tenant. Invite one by email: accepting the invitation places them here.
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <TextField
          id="tenant-email"
          label="Tenant email"
          type="email"
          autoComplete="off"
          className="min-w-56 flex-1"
          value={email}
          error={error ?? undefined}
          onChange={(event) => setEmail(event.target.value)}
        />
        <Button type="submit" variant="secondary" pending={invite.isPending}>
          Invite tenant
        </Button>
      </div>
      <p role="status" className="text-sm text-green-700">
        {sentTo ? `Invitation sent to ${sentTo}.` : ""}
      </p>
    </form>
  );
}
