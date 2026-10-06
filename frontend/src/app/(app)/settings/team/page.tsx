"use client";

import { useCurrentUser } from "@/features/auth/hooks";
import { activeMembership } from "@/features/organizations/membership";
import { InviteForm } from "@/features/team/invite-form";
import { MembersList } from "@/features/team/members-list";
import { PendingInvitations } from "@/features/team/pending-invitations";

const card = "space-y-4 rounded-lg bg-white p-6 ring-1 ring-slate-200";

export default function TeamPage() {
  const { data: user } = useCurrentUser();
  const membership = user ? activeMembership(user) : null;

  if (!user || !membership) {
    return <p className="text-sm text-slate-600">Select an organization first.</p>;
  }
  if (membership.role !== "owner" && membership.role !== "manager") {
    return <p className="text-sm text-slate-600">Only owners and managers manage the team.</p>;
  }
  const orgId = membership.organization_id;

  return (
    <div className="max-w-3xl space-y-8">
      <h1 className="text-2xl font-bold tracking-tight">Team</h1>
      <section aria-labelledby="invite-heading" className={card}>
        <h2 id="invite-heading" className="font-semibold">
          Invite someone
        </h2>
        <InviteForm key={orgId} organizationId={orgId} actorRole={membership.role} />
      </section>
      <section aria-labelledby="pending-heading" className={card}>
        <h2 id="pending-heading" className="font-semibold">
          Pending invitations
        </h2>
        <PendingInvitations organizationId={orgId} />
      </section>
      {membership.role === "owner" ? (
        <section aria-labelledby="members-heading" className={card}>
          <h2 id="members-heading" className="font-semibold">
            Members
          </h2>
          <MembersList organizationId={orgId} currentUserId={user.id} />
        </section>
      ) : null}
    </div>
  );
}
