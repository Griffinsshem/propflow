"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import type { ReactNode } from "react";

import { FormAlert } from "@/components/ui/form-alert";
import { ContractorDetailsForm } from "@/features/contractors/contractor-details-form";
import { ContractorLoginSection } from "@/features/contractors/contractor-login-section";
import { useContractor } from "@/features/contractors/hooks";
import { CONTRACTOR_STATUS_LABELS, SPECIALTY_LABELS } from "@/features/contractors/labels";
import { isStaff } from "@/features/maintenance/permissions";
import { useActiveMembership } from "@/features/organizations/use-active-membership";
import { ApiError, messageOf } from "@/lib/api/errors";

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section
      aria-labelledby={id}
      className="space-y-4 rounded-lg bg-white p-6 ring-1 ring-slate-200"
    >
      <h2 id={id} className="font-semibold">
        {title}
      </h2>
      {children}
    </section>
  );
}

const backLink = (
  <Link href="/contractors" className="text-sm font-semibold text-indigo-600 hover:text-indigo-500">
    ← Contractors
  </Link>
);

export default function ContractorPage() {
  const { contractorId } = useParams<{ contractorId: string }>();
  const membership = useActiveMembership();
  const orgId = membership?.organization_id ?? null;
  const contractor = useContractor(orgId, contractorId);

  if (!membership || orgId === null) {
    return <p className="text-sm text-slate-600">Select an organization first.</p>;
  }
  if (!isStaff(membership.role)) {
    return <p className="text-sm text-slate-600">Only owners and managers manage contractors.</p>;
  }
  if (contractor.isPending) return <p className="text-sm text-slate-500">Loading…</p>;
  if (contractor.isError) {
    const notFound = contractor.error instanceof ApiError && contractor.error.status === 404;
    return (
      <div className="space-y-4">
        {backLink}
        <FormAlert>
          {notFound ? "This contractor doesn't exist." : messageOf(contractor.error)}
        </FormAlert>
      </div>
    );
  }

  const data = contractor.data;
  return (
    <div className="max-w-3xl space-y-6">
      <div className="space-y-1">
        {backLink}
        <h1 className="text-2xl font-bold tracking-tight">{data.business_name}</h1>
        <p className="text-sm text-slate-600">
          {SPECIALTY_LABELS[data.specialty]} · {CONTRACTOR_STATUS_LABELS[data.status]}
        </p>
      </div>
      <Section id="details-heading" title="Details">
        <ContractorDetailsForm key={`${data.id}:${data.version}`} orgId={orgId} contractor={data} />
      </Section>
      <Section id="login-heading" title="Login">
        <ContractorLoginSection key={data.id} orgId={orgId} contractor={data} />
      </Section>
    </div>
  );
}
