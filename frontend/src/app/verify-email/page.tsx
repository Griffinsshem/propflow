import type { Metadata } from "next";

import { VerifyEmailPanel } from "@/features/account/verify-email-panel";

export const metadata: Metadata = { title: "Verify your email" };

export default function Page() {
  return <VerifyEmailPanel />;
}
