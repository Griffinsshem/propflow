import { z } from "zod";

export const tenantEmailSchema = z
  .string()
  .trim()
  .min(1, "Enter an email address.")
  .email("Enter a valid email address.")
  .max(320, "Use at most 320 characters.");
