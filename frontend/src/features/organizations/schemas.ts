import { z } from "zod";

export const organizationNameSchema = z.object({
  name: z.string().trim().min(1, "Enter a name.").max(200, "Use at most 200 characters."),
});

export type OrganizationNameValues = z.infer<typeof organizationNameSchema>;
