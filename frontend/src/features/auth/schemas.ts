import { z } from "zod";

// Mirrors the API's rules (backend/app/auth/schemas.py); the API remains the authority.
const email = z
  .string()
  .trim()
  .min(1, "Enter your email.")
  .email("Enter a valid email address.")
  .max(320, "Use at most 320 characters.");

export const loginSchema = z.object({
  email,
  password: z
    .string()
    .min(1, "Enter your password.")
    .max(128, "Use at most 128 characters."),
});

export const registerSchema = z.object({
  full_name: z
    .string()
    .trim()
    .min(1, "Enter your name.")
    .max(200, "Use at most 200 characters."),
  email,
  password: z
    .string()
    .min(12, "Use at least 12 characters.")
    .max(128, "Use at most 128 characters."),
});

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
