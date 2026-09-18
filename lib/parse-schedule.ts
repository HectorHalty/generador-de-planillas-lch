import type { MatchInfo, SchedulePayload } from "@/lib/types";

const CATEGORY_RE =
  /^\s*[*#_]*\s*(hombres|mujeres|masculino|femenino|caballeros|damas)\s*:?\s*[*#_]*\s*$/i;
const COURT_RE = /^\s*[*#_]*\s*cancha\s+(\d+)\s*:?\s*[*#_]*\s*$/i;
const MATCH_RE =
  /^\s*[*#-]*\s*(\d{1,2}[:.]\d{2})\s*[:.\-–]\s*(.+?)\s+vs\.?\s+(.+?)\s*[*]*\s*$/i;

const CATEGORIES: Record<string, string> = {
  hombres: "Hombres",
  masculino: "Hombres",
  caballeros: "Hombres",
  mujeres: "Mujeres",
  femenino: "Mujeres",
  damas: "Mujeres",
};

function cleanTeam(raw: string) {
  return raw.trim().replace(/^\*+|\*+$/g, "").replace(/\s+/g, " ").replace(/[;,]+$/g, "").trim();
}

function normalizeTime(raw: string) {
  const [hours, mins] = raw.split(/[:.]/);
  return `${String(Number(hours)).padStart(2, "0")}:${String(Number(mins)).padStart(2, "0")}`;
}

export function parseSchedule(text: string): SchedulePayload {
  const matches: MatchInfo[] = [];
  const errors: string[] = [];
  let category: string | null = null;
  let court: number | null = null;
  const seen = new Set<string>();

  text.split(/\r?\n/).forEach((raw, index) => {
    const line = raw.trim();
    if (!line) return;
    const categoryHit = line.match(CATEGORY_RE);
    if (categoryHit) {
      category = CATEGORIES[categoryHit[1].toLowerCase()] ?? null;
      court = null;
      return;
    }
    const courtHit = line.match(COURT_RE);
    if (courtHit) {
      court = Number(courtHit[1]);
      return;
    }
    const matchHit = line.match(MATCH_RE);
    if (matchHit) {
      if (!category) {
        errors.push(`Línea ${index + 1}: hay un partido sin categoría (Hombres/Mujeres).`);
        return;
      }
      if (court == null) {
        errors.push(`Línea ${index + 1}: hay un partido sin cancha.`);
        return;
      }
      const time = normalizeTime(matchHit[1]);
      const home = cleanTeam(matchHit[2]);
      const away = cleanTeam(matchHit[3]);
      const key = `${category}|${court}|${time}|${home}|${away}`;
      if (seen.has(key)) return;
      seen.add(key);
      matches.push({
        id: matches.length + 1,
        category,
        court,
        time,
        home,
        away,
        label: `${home} vs ${away}`,
      });
      return;
    }
    if (/\bvs\.?\b/i.test(line)) {
      errors.push(`Línea ${index + 1}: no pude leer el partido «${line}».`);
    }
  });

  const teams: string[] = [];
  const teamSeen = new Set<string>();
  for (const match of matches) {
    for (const team of [match.home, match.away]) {
      const key = team.toLowerCase();
      if (!teamSeen.has(key)) {
        teamSeen.add(key);
        teams.push(team);
      }
    }
  }
  if (matches.length === 0) {
    errors.push("No encontré partidos en el horario.");
  }
  return {
    matches,
    errors,
    teams,
    matchCount: matches.length,
    teamCount: teams.length,
  };
}
