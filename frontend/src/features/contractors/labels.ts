import { SPECIALTIES, type ContractorStatus, type Specialty } from "@/lib/api/contractors";

export const SPECIALTY_LABELS: Record<Specialty, string> = {
  general: "General",
  plumbing: "Plumbing",
  electrical: "Electrical",
  carpentry: "Carpentry",
  cleaning: "Cleaning",
  security: "Security",
  hvac: "Heating and cooling",
  painting: "Painting",
};

export const CONTRACTOR_STATUS_LABELS: Record<ContractorStatus, string> = {
  active: "Active",
  inactive: "Inactive",
};

export const SPECIALTY_OPTIONS = SPECIALTIES.map((value) => ({
  value,
  label: SPECIALTY_LABELS[value],
}));
