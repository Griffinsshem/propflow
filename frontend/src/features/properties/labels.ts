import {
  PROPERTY_STATUSES,
  PROPERTY_TYPES,
  UNIT_STATUSES,
  type PropertyStatus,
  type PropertyType,
  type UnitStatus,
} from "@/lib/api/properties";

export const PROPERTY_TYPE_LABELS: Record<PropertyType, string> = {
  residential: "Residential",
  commercial: "Commercial",
  mixed_use: "Mixed use",
  estate: "Estate",
};

export const PROPERTY_STATUS_LABELS: Record<PropertyStatus, string> = {
  active: "Active",
  archived: "Archived",
};

export const UNIT_STATUS_LABELS: Record<UnitStatus, string> = {
  vacant: "Vacant",
  occupied: "Occupied",
  unavailable: "Unavailable",
};

export const PROPERTY_TYPE_OPTIONS = PROPERTY_TYPES.map((value) => ({
  value,
  label: PROPERTY_TYPE_LABELS[value],
}));
export const PROPERTY_STATUS_OPTIONS = PROPERTY_STATUSES.map((value) => ({
  value,
  label: PROPERTY_STATUS_LABELS[value],
}));
export const UNIT_STATUS_OPTIONS = UNIT_STATUSES.map((value) => ({
  value,
  label: UNIT_STATUS_LABELS[value],
}));
