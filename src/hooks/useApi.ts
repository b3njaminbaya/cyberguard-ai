import { useSyncExternalStore } from "react"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { getRealtimeEnabled, subscribeRealtimePreference } from "@/lib/realtimePreference"

const REFETCH_MS = 15_000

function useRefetchInterval() {
  const enabled = useSyncExternalStore(subscribeRealtimePreference, getRealtimeEnabled, () => true)
  return enabled ? REFETCH_MS : false
}

export function useThreats(limit = 50) {
  const refetchInterval = useRefetchInterval()
  return useQuery({
    queryKey: ["threats", limit],
    queryFn: () => api.threats(limit),
    refetchInterval,
  })
}

export function useEvents(limit = 50) {
  const refetchInterval = useRefetchInterval()
  return useQuery({
    queryKey: ["events", limit],
    queryFn: () => api.events(limit),
    refetchInterval,
  })
}

export function useSummary() {
  const refetchInterval = useRefetchInterval()
  return useQuery({
    queryKey: ["summary"],
    queryFn: api.summary,
    refetchInterval,
  })
}

export function useModelMetrics() {
  return useQuery({
    queryKey: ["model-metrics"],
    queryFn: api.modelMetrics,
  })
}

export function useLogs(params: { limit?: number; severity?: string; flaggedOnly?: boolean; search?: string } = {}) {
  const refetchInterval = useRefetchInterval()
  return useQuery({
    queryKey: ["logs", params],
    queryFn: () => api.logs(params),
    refetchInterval,
  })
}

export function useLogStats() {
  const refetchInterval = useRefetchInterval()
  return useQuery({
    queryKey: ["log-stats"],
    queryFn: api.logStats,
    refetchInterval,
  })
}
