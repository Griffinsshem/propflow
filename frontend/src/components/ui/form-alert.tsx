import type { ReactNode } from "react";

export function FormAlert({ children }: { children: ReactNode }) {
  return (
    <div
      role="alert"
      className="rounded-md bg-red-50 p-3 text-sm text-red-700 ring-1 ring-red-200"
    >
      {children}
    </div>
  );
}
