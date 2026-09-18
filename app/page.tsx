import { readFile } from "node:fs/promises";
import path from "node:path";

import { PlanilleroApp } from "@/components/planillero-app";

export default async function Home() {
  const defaultSchedule = await readFile(
    path.join(process.cwd(), "public", "horario-jornada.txt"),
    "utf8",
  );
  return <PlanilleroApp defaultSchedule={defaultSchedule} />;
}
