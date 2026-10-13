"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/lib/api/errors";
import { propertiesApi, unitsApi, type PropertyStatus } from "@/lib/api/properties";

const NONE = "none";

export const propertyKeys = {
  lists: (orgId: string) => ["org", orgId, "properties"] as const,
  list: (orgId: string, status: PropertyStatus) => ["org", orgId, "properties", status] as const,
  detail: (orgId: string, id: string) => ["org", orgId, "property", id] as const,
  buildings: (orgId: string, id: string) => ["org", orgId, "property", id, "buildings"] as const,
  managers: (orgId: string, id: string) => ["org", orgId, "property", id, "managers"] as const,
  units: (orgId: string, id: string) => ["org", orgId, "property", id, "units"] as const,
  unit: (orgId: string, id: string) => ["org", orgId, "unit", id] as const,
};

// A 404 is an answer (missing, or not visible to this user), not a failure worth retrying.
const retryUnlessNotFound = (failures: number, error: unknown) =>
  !(error instanceof ApiError && error.status === 404) && failures < 2;

export function useProperties(orgId: string | null, status: PropertyStatus) {
  return useQuery({
    queryKey: propertyKeys.list(orgId ?? NONE, status),
    queryFn: ({ signal }) => propertiesApi.list(status, signal),
    enabled: orgId !== null,
  });
}

export function useProperty(orgId: string | null, id: string) {
  return useQuery({
    queryKey: propertyKeys.detail(orgId ?? NONE, id),
    queryFn: ({ signal }) => propertiesApi.get(id, signal),
    enabled: orgId !== null,
    retry: retryUnlessNotFound,
  });
}

export function useBuildings(orgId: string, propertyId: string) {
  return useQuery({
    queryKey: propertyKeys.buildings(orgId, propertyId),
    queryFn: ({ signal }) => propertiesApi.listBuildings(propertyId, signal),
  });
}

export function usePropertyManagers(orgId: string, propertyId: string) {
  return useQuery({
    queryKey: propertyKeys.managers(orgId, propertyId),
    queryFn: ({ signal }) => propertiesApi.listManagers(propertyId, signal),
  });
}

export function useUnits(orgId: string, propertyId: string) {
  return useQuery({
    queryKey: propertyKeys.units(orgId, propertyId),
    queryFn: ({ signal }) => unitsApi.listForProperty(propertyId, signal),
  });
}

export function useUnit(orgId: string | null, id: string) {
  return useQuery({
    queryKey: propertyKeys.unit(orgId ?? NONE, id),
    queryFn: ({ signal }) => unitsApi.get(id, signal),
    enabled: orgId !== null,
    retry: retryUnlessNotFound,
  });
}

export function useCreateProperty(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: propertiesApi.create,
    onSuccess: async (property) => {
      queryClient.setQueryData(propertyKeys.detail(orgId, property.id), property);
      await queryClient.invalidateQueries({
        queryKey: propertyKeys.lists(orgId),
      });
    },
  });
}

export function useUpdateProperty(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: propertiesApi.update,
    onSuccess: async (property) => {
      queryClient.setQueryData(propertyKeys.detail(orgId, property.id), property);
      await queryClient.invalidateQueries({
        queryKey: propertyKeys.lists(orgId),
      });
    },
  });
}

export function useCreateBuilding(orgId: string, propertyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => propertiesApi.createBuilding({ propertyId, name }),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: propertyKeys.buildings(orgId, propertyId),
      }),
  });
}

export function useAssignManager(orgId: string, propertyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (membershipId: string) => propertiesApi.assignManager({ propertyId, membershipId }),
    onSettled: () =>
      queryClient.invalidateQueries({
        queryKey: propertyKeys.managers(orgId, propertyId),
      }),
  });
}

export function useUnassignManager(orgId: string, propertyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (membershipId: string) =>
      propertiesApi.unassignManager({ propertyId, membershipId }),
    onSettled: () =>
      queryClient.invalidateQueries({
        queryKey: propertyKeys.managers(orgId, propertyId),
      }),
  });
}

export function useCreateUnit(orgId: string, propertyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: unitsApi.create,
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: propertyKeys.units(orgId, propertyId),
      }),
  });
}

export function useUpdateUnit(orgId: string, propertyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: unitsApi.update,
    onSuccess: async (unit) => {
      queryClient.setQueryData(propertyKeys.unit(orgId, unit.id), unit);
      await queryClient.invalidateQueries({
        queryKey: propertyKeys.units(orgId, propertyId),
      });
    },
  });
}
