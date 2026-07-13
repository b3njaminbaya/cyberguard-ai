import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"

const REFETCH_MS = 15_000

export function useThreats(limit = 50) {
  return useQuery({
    queryKey: ["threats", limit],
    queryFn: () => api.threats(limit),
    refetchInterval: REFETCH_MS,
  })
}

export function useEvents(limit = 50) {
  return useQuery({
    queryKey: ["events", limit],
    queryFn: () => api.events(limit),
    refetchInterval: REFETCH_MS,
  })
}

export function useSummary() {
  return useQuery({
    queryKey: ["summary"],
    queryFn: api.summary,
    refetchInterval: REFETCH_MS,
  })
}

export function useModelMetrics() {
  return useQuery({
    queryKey: ["model-metrics"],
    queryFn: api.modelMetrics,
  })
}
