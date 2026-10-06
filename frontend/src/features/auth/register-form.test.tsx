import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { RegisterForm } from "./register-form";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }) }));
vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

describe("RegisterForm", () => {
  it("validates input before calling the API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(
      <QueryClientProvider client={new QueryClient()}>
        <RegisterForm />
      </QueryClientProvider>,
    );

    await userEvent.type(screen.getByLabelText("Full name"), "Erin Example");
    await userEvent.type(screen.getByLabelText("Email"), "erin@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "short");
    await userEvent.click(
      screen.getByRole("button", { name: "Create account" }),
    );

    expect(
      await screen.findByText("Use at least 12 characters."),
    ).toBeVisible();
    expect(screen.getByLabelText("Password")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
