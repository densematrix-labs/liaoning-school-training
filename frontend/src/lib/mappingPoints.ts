export function mappingPoints(mapping: Record<string, string[]>, steps: any[], configured: any = {}) {
  return Object.fromEntries(Object.entries(mapping).map(([stepId, subs]) => [stepId,
    Object.fromEntries(subs.map(id => [id, configured[stepId]?.[id] ?? steps.find(s => String(s.id) === stepId)?.score ?? 1]))
  ]))
}
