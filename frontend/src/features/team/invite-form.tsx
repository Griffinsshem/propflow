"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { TextField } from "@/components/ui/text-field";
import { useCreateInvitation } from "@/features/team/hooks";
import { invitableRoles, ROLE_LABELS } from "@/features/team/policy";
import { inviteSchema, type InviteValues } from "@/features/team/schemas";
import type { Role } from "@/lib/api/auth";
import { ApiError, messageOf } from "@/lib/api/errors";

export function InviteForm({
  organizationId,
  actorRole,
}: {
  organizationId: string;
  actorRole: Role;
}) {
  const roles = invitableRoles(actorRole);
  const create = useCreateInvitation(organizationId);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<InviteValues>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { email: "", role: roles[0] },
  });

  const onSubmit = handleSubmit(async (values) => {
    setSentTo(null);
    setFormError(null);
    try {
      await create.mutateAsync(values);
      setSentTo(values.email);
      reset({ email: "", role: values.role });
    } catch (error) {
      const emailError =
        error instanceof ApiError ? error.fieldErrors.email?.[0] : undefined;
      if (emailError) {
        setError("email", { type: "server", message: emailError });
      } else if (error instanceof ApiError && error.status === 429) {
        setFormError(
          "You've sent many invitations recently. Please try again later.",
        );
      } else {
        setFormError(messageOf(error));
      }
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4">
      {formError ? <FormAlert>{formError}</FormAlert> : null}
      <div className="grid gap-4 sm:grid-cols-[1fr_12rem]">
        <TextField
          id="invite-email"
          label="Email address"
          type="email"
          autoComplete="off"
          error={errors.email?.message}
          {...register("email")}
        />
        <div>
          <label
            htmlFor="invite-role"
            className="block text-sm font-medium text-slate-900"
          >
            Role
          </label>
          <select
            id="invite-role"
            className="mt-1.5 block w-full rounded-md border-0 py-2 pl-3 pr-8 text-sm text-slate-900 ring-1 ring-inset ring-slate-300 focus:ring-2 focus:ring-indigo-600"
            {...register("role")}
          >
            {roles.map((role) => (
              <option key={role} value={role}>
                {ROLE_LABELS[role]}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Button type="submit" pending={isSubmitting}>
          {isSubmitting ? "Sending…" : "Send invitation"}
        </Button>
        <p role="status" className="text-sm text-green-700">
          {sentTo ? `Invitation sent to ${sentTo}.` : ""}
        </p>
      </div>
    </form>
  );
}
