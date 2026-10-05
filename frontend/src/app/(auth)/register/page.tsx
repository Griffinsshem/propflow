import type { Metadata } from "next";

import { RegisterForm } from "@/features/auth/register-form";

export const metadata: Metadata = { title: "Create an account" };

export default function RegisterPage() {
  return (
    <>
      <h1 className="text-xl font-semibold">Create your PropFlow account</h1>
      <div className="mt-6">
        <RegisterForm />
      </div>
    </>
  );
}
