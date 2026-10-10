import { apiRequest } from "./client";

export const accountApi = {
  /** Always 202 with the same message, whether or not the account exists. */
  forgotPassword: (email: string) =>
    apiRequest<{ message: string }>("/auth/forgot-password", { method: "POST", body: { email } }),
  resetPassword: ({ token, newPassword }: { token: string; newPassword: string }) =>
    apiRequest<void>("/auth/reset-password", {
      method: "POST",
      body: { token, new_password: newPassword },
    }),
  verifyEmail: (token: string) =>
    apiRequest<void>("/auth/verify-email", { method: "POST", body: { token } }),
  resendVerification: () =>
    apiRequest<{ message: string }>("/auth/resend-verification", { method: "POST" }),
};
