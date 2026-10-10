import { z } from "zod";

// Mirrors the API's rules (backend/app/auth/schemas.py); the API remains the authority.
export const emailSchema = z.object({
  email: z
    .string()
    .trim()
    .min(1, "Enter your email address.")
    .email("Enter a valid email address.")
    .max(320, "Use at most 320 characters."),
});
export type EmailValues = z.infer<typeof emailSchema>;

export const newPasswordSchema = z
  .object({
    password: z
      .string()
      .min(12, "Use at least 12 characters.")
      .max(128, "Use at most 128 characters."),
    confirm: z.string(),
  })
  .refine((values) => values.password === values.confirm, {
    message: "The passwords don't match.",
    path: ["confirm"],
  });
export type NewPasswordValues = z.infer<typeof newPasswordSchema>;
