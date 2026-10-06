"use client";

import { FormAlert } from "@/components/ui/form-alert";
import { useCurrentUser } from "@/features/auth/hooks";
import { useOrganization } from "@/features/organizations/hooks";
import { activeMembership } from "@/features/organizations/membership";
import { RenameOrganizationForm } from "@/features/organizations/rename-organization-form";

export default function OrganizationSettingsPage() {
  const { data: user } = useCurrentUser();
  const membership = user ? activeMembership(user) : null;
  const organization = useOrganization(membership?.organization_id ?? null);

  if (!membership) {
    return <p className="text-sm text-slate-600">Select an organization first.</p>;
  }
  if (organization.isPending) {
    return <p className="text-sm text-slate-500">Loading…</p>;
  }
  if (organization.isError) {
    return <FormAlert>We couldn&apos;t load this organization. Please try again.</FormAlert>;
  }

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Organization</h1>
      {membership.role === "owner" ? (
        <RenameOrganizationForm key={organization.data.id} organization={organization.data} />
      ) : (
        <dl className="space-y-3 rounded-lg bg-white p-6 text-sm ring-1 ring-slate-200">
          <div>
            <dt className="font-medium text-slate-900">Name</dt>
            <dd className="text-slate-700">{organization.data.name}</dd>
          </div>
          <div>
            <dt className="font-medium text-slate-900">Your role</dt>
            <dd className="capitalize text-slate-700">{membership.role}</dd>
          </div>
          <p className="text-slate-500">Only owners can change organization settings.</p>
        </dl>
      )}
    </div>
  );
}
