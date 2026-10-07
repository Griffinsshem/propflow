import { z } from "zod";

import { hasControlCharacters } from "@/features/maintenance/schemas";
import {
  CONTRACTOR_STATUSES,
  SPECIALTIES,
  type Contractor,
  type ContractorChanges,
  type ContractorInput,
} from "@/lib/api/contractors";

// Mirrors the API's rules (backend/app/contractors/schemas.py); the API remains the authority.
const E164 = /^\+[1-9][0-9]{7,14}$/;
const plain = (value: string) => !hasControlCharacters(value);
const isEmail = (value: string) => z.string().email().safeParse(value).success;

export const contractorSchema = z.object({
  business_name: z
    .string()
    .trim()
    .min(1, "Enter the business name.")
    .max(200, "Use at most 200 characters.")
    .refine(plain, "Remove unsupported characters."),
  contact_name: z
    .string()
    .trim()
    .max(200, "Use at most 200 characters.")
    .refine(plain, "Remove unsupported characters."),
  phone: z
    .string()
    .trim()
    .refine((value) => value === "" || E164.test(value), {
      message: "Use international format, e.g. +254712345678.",
    }),
  email: z
    .string()
    .trim()
    .max(320, "Use at most 320 characters.")
    .refine((value) => value === "" || isEmail(value), { message: "Enter a valid email address." }),
  specialty: z.enum(SPECIALTIES),
  status: z.enum(CONTRACTOR_STATUSES),
});

export type ContractorFormValues = z.infer<typeof contractorSchema>;

export const CONTRACTOR_FIELDS = [
  "business_name",
  "contact_name",
  "phone",
  "email",
  "specialty",
  "status",
] as const;

export const EMPTY_CONTRACTOR: ContractorFormValues = {
  business_name: "",
  contact_name: "",
  phone: "",
  email: "",
  specialty: "general",
  status: "active",
};

export function contractorFormValues(contractor: Contractor): ContractorFormValues {
  return {
    business_name: contractor.business_name,
    contact_name: contractor.contact_name ?? "",
    phone: contractor.phone ?? "",
    email: contractor.email ?? "",
    specialty: contractor.specialty,
    status: contractor.status,
  };
}

/** Create payload: new contractors are always active, so status is not sent. */
export function toContractorInput(values: ContractorFormValues): ContractorInput {
  return {
    business_name: values.business_name,
    contact_name: values.contact_name || null,
    phone: values.phone || null,
    email: values.email || null,
    specialty: values.specialty,
  };
}

const OPTIONAL = new Set(["contact_name", "phone", "email"]);

export function toContractorChanges(changes: Partial<ContractorFormValues>): ContractorChanges {
  return Object.fromEntries(
    Object.entries(changes).map(([key, value]) => [
      key,
      OPTIONAL.has(key) && value === "" ? null : value,
    ]),
  ) as ContractorChanges;
}
