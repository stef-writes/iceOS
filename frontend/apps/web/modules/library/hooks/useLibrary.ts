"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { library as api } from "@/modules/api/client";

export type ListParams = {
  org_id?: string;
  user_id?: string;
  prefix?: string;
  limit?: number;
};

export function useAssetsList(params: ListParams) {
  return useQuery({
    queryKey: ["library", "assets", params],
    queryFn: () => api.assets.list(params),
    staleTime: 10_000,
  });
}

export function useCreateAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { label: string; content: string; mime?: string; scope?: string; org_id?: string; user_id?: string }) =>
      api.assets.create(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["library", "assets"] });
    },
  });
}

export function useDeleteAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ label, params }: { label: string; params?: { org_id?: string; user_id?: string } }) =>
      api.assets.delete(label, params ?? {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["library", "assets"] });
    },
  });
}
