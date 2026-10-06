import type { Metadata } from "next";

import { AcceptInvitation } from "@/features/team/accept-invitation";

export const metadata: Metadata = { title: "Accept invitation" };

export default function AcceptInvitePage() {
  return <AcceptInvitation />;
}
