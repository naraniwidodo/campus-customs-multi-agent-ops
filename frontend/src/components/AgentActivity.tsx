import type { ActivityRecord } from "../types";

/** Which audit events are worth showing a human, and how to label them. */
const EVENT_LABEL: Record<string, string> = {
  boss_decision: "routed the work",
  agent_response: "reported back",
  agent_failed: "could not complete the task",
  invalid_delegation: "dropped an invalid delegation",
  final_answer: "wrote the final answer",
};

const SHOWN = new Set(Object.keys(EVENT_LABEL));

/** One or two sentences. Agent summaries can run long; the panel is a scan, not a read. */
function brief(text: string, maxSentences = 2): string {
  const sentences = text.replace(/\s+/g, " ").trim().match(/[^.!?]+[.!?]?/g) ?? [text];
  const kept = sentences.slice(0, maxSentences).join("").trim();
  return kept.length < text.trim().length ? `${kept.replace(/[.\s]*$/, "")}…` : kept;
}

interface Props {
  records: ActivityRecord[];
  running: boolean;
}

export function AgentActivity({ records, running }: Props) {
  const rows = records.filter((r) => SHOWN.has(r.event));

  if (!rows.length) {
    return (
      <div className="empty">
        {running
          ? "The team is starting…"
          : "No agent activity yet. Pick a ticket and run the team."}
      </div>
    );
  }

  return (
    <div>
      {rows.map((r, i) => {
        const who = r.event === "final_answer" ? "boss" : r.agent ?? "boss";
        const isBoss = who === "boss" || who.startsWith("boss");
        // A new run_id means a fresh pass over the ticket — usually one the human
        // triggered by approving something. Mark it so the sequence stays legible.
        const newRun = i > 0 && rows[i - 1].run_id !== r.run_id;
        return (
          <div className="agent-row" key={r.record_id}>
            {newRun && <div className="run-divider">— agents resumed —</div>}
            <div className="agent-head">
              <span className={`agent-name ${isBoss ? "boss" : ""}`}>
                {who.replace(/_/g, " ")}
              </span>
              <span className="round">
                {r.iteration ? `round ${r.iteration} · ` : ""}
                {EVENT_LABEL[r.event]}
                {r.answered === false ? " · could not answer" : ""}
              </span>
            </div>

            {r.message && <div className="agent-summary">{brief(r.message)}</div>}

            {r.tools_used.length > 0 && (
              <div className="tool-list">
                {r.tools_used.map((t, i) => (
                  <span className={`tool ${t.ok === false ? "failed" : ""}`} key={i}>
                    {t.tool}
                    {t.ok === false ? " — failed" : ""}
                  </span>
                ))}
              </div>
            )}

            {r.missing.length > 0 && (
              <div className="missing">
                Could not determine: {r.missing.join("; ")}
              </div>
            )}

            {r.draft_message && (
              <div className="draft">
                <span className="draft-tag">Draft — not sent</span>
                {r.draft_message}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
