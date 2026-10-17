"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useSyncExternalStore, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { CURRENT_USER_KEY, useCurrentUser } from "@/features/auth/hooks";
import { LoginForm } from "@/features/auth/login-form";
import { RegisterForm } from "@/features/auth/register-form";
import { ROLE_LABELS } from "@/features/team/policy";
import { authApi } from "@/lib/api/auth";
import { ApiError, messageOf } from "@/lib/api/errors";
import { invitationsApi } from "@/lib/api/invitations";

// The token arrives in the URL fragment, which browsers never send to any server.
const TOKEN = /(?:^#|&)token=([A-Za-z0-9_.-]+)/;

function subscribeToHash(onChange: () => void) {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

function acceptErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.code === "INVALID_TOKEN") {
    return "This invitation is invalid or has expired. Ask for a new one.";
  }
  return messageOf(error);
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <p className="mb-8 text-center text-2xl font-bold tracking-tight text-indigo-600">
          <Link href="/" className="hover:opacity-80">
            PropFlow
          </Link>
        </p>
        <div className="space-y-5 rounded-xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
          <h1 className="text-xl font-semibold">{title}</h1>
          {children}
        </div>
      </div>
    </main>
  );
}

export function AcceptInvitation() {
  const hash = useSyncExternalStore(
    subscribeToHash,
    () => window.location.hash,
    () => null,
  );
  const token = hash === null ? undefined : (TOKEN.exec(hash)?.[1] ?? null);
  const router = useRouter();
  const queryClient = useQueryClient();
  const me = useCurrentUser();
  const preview = useQuery({
    queryKey: ["invitation-preview", token],
    queryFn: () => invitationsApi.preview(token ?? ""),
    enabled: typeof token === "string",
    retry: false,
  });
  const [mode, setMode] = useState<"register" | "login">("register");
  const [accepting, setAccepting] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [acceptError, setAcceptError] = useState<string | null>(null);

  async function accept(): Promise<void> {
    if (!token) return;
    setAccepting(true);
    setAcceptError(null);
    try {
      await invitationsApi.accept(token);
      // The session now works in the new organization: drop anything cached for another.
      queryClient.removeQueries({
        predicate: (query) => query.queryKey[0] !== "auth",
      });
      await queryClient.invalidateQueries({ queryKey: CURRENT_USER_KEY });
      router.replace("/dashboard");
    } catch (error) {
      setAcceptError(acceptErrorMessage(error));
      setAccepting(false);
    }
  }

  async function signOutHere(): Promise<void> {
    setSigningOut(true);
    try {
      await authApi.logout();
    } finally {
      queryClient.clear(); // stays on this page, so the invitation link is not lost
      setSigningOut(false);
    }
  }

  if (token === undefined || (token !== null && preview.isPending)) {
    return (
      <Card title="Invitation">
        <p className="text-sm text-slate-500">Loading invitation…</p>
      </Card>
    );
  }
  if (token === null || preview.isError) {
    return (
      <Card title="Invitation unavailable">
        <p className="text-sm text-slate-600">
          This invitation is invalid or has expired. Ask the person who invited you to send a new
          one.
        </p>
      </Card>
    );
  }

  const invitation = preview.data;
  if (invitation === undefined) {
    return (
      <Card title="Invitation">
        <p className="text-sm text-slate-500">Loading invitation…</p>
      </Card>
    );
  }
  const user = me.data;
  const sameAddress = user?.email.toLowerCase() === invitation.email.toLowerCase();

  return (
    <Card title={`Join ${invitation.organization_name}`}>
      <p className="text-sm text-slate-600">
        You&apos;ve been invited as <strong>{ROLE_LABELS[invitation.role]}</strong> using{" "}
        <strong>{invitation.email}</strong>.
      </p>
      {acceptError ? <FormAlert>{acceptError}</FormAlert> : null}

      {me.isPending ? (
        <p className="text-sm text-slate-500">Checking your session…</p>
      ) : user && sameAddress ? (
        <Button type="button" className="w-full" pending={accepting} onClick={accept}>
          {accepting ? "Joining…" : "Accept invitation"}
        </Button>
      ) : user ? (
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            You&apos;re signed in as {user.email}. This invitation is for {invitation.email}.
          </p>
          <Button
            type="button"
            variant="secondary"
            className="w-full"
            pending={signingOut}
            onClick={signOutHere}
          >
            Sign out and continue
          </Button>
        </div>
      ) : mode === "register" ? (
        <div className="space-y-4">
          <RegisterForm email={invitation.email} onSuccess={accept} showLoginLink={false} />
          <button
            type="button"
            className="w-full text-center text-sm font-semibold text-indigo-600 hover:text-indigo-500"
            onClick={() => setMode("login")}
          >
            I already have an account
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <LoginForm email={invitation.email} onSuccess={accept} showRegisterLink={false} />
          <button
            type="button"
            className="w-full text-center text-sm font-semibold text-indigo-600 hover:text-indigo-500"
            onClick={() => setMode("register")}
          >
            Create a new account instead
          </button>
        </div>
      )}
    </Card>
  );
}
