export function compactClientSummary(
  summary: Record<string, unknown>,
  extra: Record<string, unknown> = {},
) {
  const schedule = (summary.schedule ?? {}) as Record<string, unknown>;
  return {
    ok: summary.ok,
    pageCount: summary.pageCount,
    outputPages: summary.outputPages,
    keptOriginalPages: summary.keptOriginalPages,
    createdPlanillas: summary.createdPlanillas,
    removedTeams: summary.removedTeams ?? [],
    unmatchedMatches: summary.unmatchedMatches ?? [],
    warnings: summary.warnings ?? [],
    matchDate: summary.matchDate,
    schedule: {
      matchCount: schedule.matchCount ?? 0,
      teamCount: schedule.teamCount ?? 0,
      errors: schedule.errors ?? [],
    },
    ...extra,
  };
}
