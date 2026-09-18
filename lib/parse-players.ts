export type ParsedPlayers = {
  players: { name: string; team: string; raw: string }[];
  errors: string[];
};

const PLAYER_LINE = /^\s*(.+?)\s*\(\s*(.+?)\s*\)\s*$/;
const LIST_PREFIX = /^[-*•·#]+\s*/;
const HEADER_LINE = /^(suspendidos?|jugadores?|lista|sancionados?)\s*:?\s*$/i;

export function parsePlayers(text: string): ParsedPlayers {
  const players: ParsedPlayers["players"] = [];
  const errors: string[] = [];
  const seen = new Set<string>();

  text.split(/\r?\n/).forEach((raw, index) => {
    let line = raw.trim().replace(LIST_PREFIX, "").trim();
    if (!line) return;
    if (HEADER_LINE.test(line) || (line.endsWith(":") && !line.includes("("))) return;
    const hit = PLAYER_LINE.exec(line);
    if (!hit) {
      errors.push(
        `Línea ${index + 1}: usá el formato Nombre Apellido (Equipo), por ejemplo Ezequiel Guzman (Mimetizarte).`,
      );
      return;
    }
    const name = hit[1].replace(/\s+/g, " ").replace(/^[\s-]+|[\s-]+$/g, "");
    const team = hit[2].replace(/\s+/g, " ").replace(/^[\s-]+|[\s-]+$/g, "");
    if (name.length < 3 || team.length < 2) {
      errors.push(`Línea ${index + 1}: faltan el nombre o el equipo.`);
      return;
    }
    const key = `${name.toLowerCase()}|${team.toLowerCase()}`;
    if (seen.has(key)) return;
    seen.add(key);
    players.push({ name, team, raw: `${name} (${team})` });
  });

  return { players, errors };
}
