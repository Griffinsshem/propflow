"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { FormAlert } from "@/components/ui/form-alert";
import { ActivityFeed } from "@/features/maintenance/activity-feed";
import { CommentForm } from "@/features/maintenance/comment-form";
import { useMaintenanceRequest } from "@/features/maintenance/hooks";
import { StatusActions } from "@/features/maintenance/status-actions";
import { PhotoGallery } from "@/features/maintenance/photo-gallery";
import { PhotoUploader } from "@/features/maintenance/photo-uploader";
import { CATEGORY_LABELS, locationOf, PRIORITY_LABELS } from "@/features/maintenance/labels";
import { StatusBadge } from "@/features/maintenance/status-badge";
import { useActiveMembership } from "@/features/organizations/use-active-membership";
import { ApiError, messageOf } from "@/lib/api/errors";
import { formatDate } from "@/lib/format";

const backLink = (
  <Link href="/maintenance" className="text-sm font-semibold text-indigo-600 hover:text-indigo-500">
    ← Maintenance
  </Link>
);

export default function MaintenanceRequestPage() {
  const { requestId } = useParams<{ requestId: string }>();
  const membership = useActiveMembership();
  const request = useMaintenanceRequest(membership?.organization_id ?? null, requestId);

  if (!membership) return <p className="text-sm text-slate-600">Select an organization first.</p>;
  if (request.isPending) return <p className="text-sm text-slate-500">Loading…</p>;
  if (request.isError) {
    const notFound = request.error instanceof ApiError && request.error.status === 404;
    return (
      <div className="space-y-4">
        {backLink}
        <FormAlert>
          {notFound
            ? "This request doesn't exist, or it isn't visible to you."
            : messageOf(request.error)}
        </FormAlert>
      </div>
    );
  }

  const data = request.data;
  const details: [string, string][] = [
    ["Location", locationOf(data)],
    ["Priority", PRIORITY_LABELS[data.priority]],
    ["Category", CATEGORY_LABELS[data.category]],
    ["Reported by", data.reported_by.full_name],
    ["Reported on", formatDate(data.created_at)],
  ];

  return (
    <div className="max-w-3xl space-y-6">
      <div className="space-y-2">
        {backLink}
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight">{data.title}</h1>
          <StatusBadge status={data.status} />
        </div>
      </div>
      <StatusActions orgId={membership.organization_id} request={data} />
      <section className="space-y-5 rounded-lg bg-white p-6 ring-1 ring-slate-200">
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          {details.map(([term, value]) => (
            <div key={term}>
              <dt className="font-medium text-slate-900">{term}</dt>
              <dd className="text-slate-700">{value}</dd>
            </div>
          ))}
        </dl>
        <div className="space-y-1 text-sm">
          <h2 className="font-medium text-slate-900">Description</h2>
          {/* Plain text, rendered as text: user input can never become markup. */}
          <p className="whitespace-pre-wrap text-slate-700">{data.description}</p>
        </div>
        {data.access_notes ? (
          <div className="space-y-1 text-sm">
            <h2 className="font-medium text-slate-900">Access notes</h2>
            <p className="whitespace-pre-wrap text-slate-700">{data.access_notes}</p>
          </div>
        ) : null}
      </section>
      <section
        aria-labelledby="photos-heading"
        className="space-y-4 rounded-lg bg-white p-6 ring-1 ring-slate-200"
      >
        <h2 id="photos-heading" className="font-semibold">
          Photos
        </h2>
        <PhotoGallery orgId={membership.organization_id} requestId={data.id} />
        {data.status !== "closed" ? (
          <PhotoUploader orgId={membership.organization_id} requestId={data.id} />
        ) : null}
      </section>
      <section
        aria-labelledby="activity-heading"
        className="space-y-4 rounded-lg bg-white p-6 ring-1 ring-slate-200"
      >
        <h2 id="activity-heading" className="font-semibold">
          Activity
        </h2>
        <ActivityFeed orgId={membership.organization_id} requestId={data.id} />
        <CommentForm orgId={membership.organization_id} requestId={data.id} />
      </section>
    </div>
  );
}
