import { z } from "zod";

export const inviteSchema = z.object({
  email: z
    .string()
    .trim()
    .min(1, "Enter an email address.")
    .email("Enter a valid email address.")
    .max(320, "Use at most 320 characters."),
  role: z.enum(["owner", "manager", "tenant", "contractor"]),
});

export type InviteValues = z.infer<typeof inviteSchema>;
