import type { Metadata } from "next";

import { LoginForm } from "@/features/auth/login-form";
import { safeNextPath } from "@/features/auth/redirect";

export const metadata: Metadata = { title: "Sign in" };

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

export default async function LoginPage({ searchParams }: Props) {
  const { next } = await searchParams;
  return (
    <>
      <h1 className="text-xl font-semibold">Sign in to PropFlow</h1>
      <div className="mt-6">
        <LoginForm next={safeNextPath(next)} />
      </div>
    </>
  );
}
