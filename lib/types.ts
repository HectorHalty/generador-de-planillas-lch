export type MatchInfo = {
  id: number;
  category: string;
  court: number;
  time: string;
  home: string;
  away: string;
  label: string;
};

export type SchedulePayload = {
  matches: MatchInfo[];
  errors: string[];
  teams: string[];
  matchCount: number;
  teamCount: number;
};

export type ProcessSummary = {
  ok: boolean;
  error?: string;
  downloadUrl?: string;
  schedule?: Partial<SchedulePayload> & {
    matchCount?: number;
    teamCount?: number;
    errors?: string[];
  };
  pageCount?: number;
  removedPages?: {
    page: number;
    teams: string[];
    extraTeams?: string[];
    reason: string;
  }[];
  removedTeams?: string[];
  unmatchedMatches?: MatchInfo[];
  warnings?: string[];
  keptPages?: {
    page: number;
    matchId: number | null;
    teams: string[];
    reason: string;
  }[];
  outputPages?: number;
  keptOriginalPages?: number;
  createdPlanillas?: number;
  matchDate?: string;
};
