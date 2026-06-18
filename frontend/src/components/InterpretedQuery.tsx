import type { InterpretedQuery } from "@/lib/types";
import { Tag } from "./Badges";

/** Shows how the natural-language query was parsed by the backend. */
export default function InterpretedQueryChips({ q }: { q: InterpretedQuery }) {
  const chips: string[] = [];
  if (q.player_name) chips.push(q.player_name);
  if (q.year) chips.push(String(q.year));
  if (q.brand) chips.push(q.brand);
  if (q.set_name) chips.push(q.set_name);
  if (q.card_number) chips.push(`#${q.card_number}`);
  if (q.parallel) chips.push(q.parallel);
  if (q.is_rookie) chips.push("Rookie");
  if (q.grading_company && q.grade) chips.push(`${q.grading_company} ${q.grade}`);

  if (chips.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-sm text-slate-500">Interpreted as</span>
      {chips.map((c, i) => (
        <Tag key={i}>{c}</Tag>
      ))}
    </div>
  );
}
