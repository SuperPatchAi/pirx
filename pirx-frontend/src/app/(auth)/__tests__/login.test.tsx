import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import LoginPage from "../login/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: {
      signInWithPassword: vi.fn(),
      signInWithOtp: vi.fn(),
    },
  }),
}));

describe("LoginPage", () => {
  it("renders sign in form", () => {
    render(<LoginPage />);
    expect(screen.getByText("Sign In")).toBeDefined();
  });

  it("has email and password inputs", () => {
    render(<LoginPage />);
    expect(screen.getByLabelText(/email/i)).toBeDefined();
    expect(screen.getByLabelText(/password/i)).toBeDefined();
  });

  it("has link to signup", () => {
    render(<LoginPage />);
    expect(screen.getByText(/sign up/i)).toBeDefined();
  });

  it("renders PIRX branding", () => {
    render(<LoginPage />);
    expect(screen.getByText("PIRX")).toBeDefined();
    expect(screen.getByText("Performance Intelligence")).toBeDefined();
  });
});
