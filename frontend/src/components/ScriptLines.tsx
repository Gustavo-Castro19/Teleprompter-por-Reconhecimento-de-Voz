import type { PromptLine } from "../lib/scriptModel";
import type { TeleprompterLayout } from "../lib/teleprompterLayout";

type ScriptLinesProps = {
  lines: PromptLine[];
  cursor: number;
  layout: TeleprompterLayout;
  emptyMessage?: string;
};

export function ScriptLines({
  lines,
  cursor,
  layout,
  emptyMessage = "Importe um roteiro para exibir o texto completo.",
}: ScriptLinesProps) {
  if (lines.length === 0) {
    return <p className="text-base opacity-60">{emptyMessage}</p>;
  }

  return (
    <>
      {lines.map((line) => (
        <p
          key={line.id}
          className="mb-5"
          data-script-line=""
          data-line-id={line.id}
          data-retranca-id={line.retrancaId}
        >
          <span
            className={
              line.technical ? "bg-white px-2 py-0.5 text-black" : ""
            }
          >
            {line.words.map((word, index) => {
              const start = word.scriptIndex;
              const end = word.scriptIndexEnd;
              const isCurrent =
                start !== null &&
                end !== null &&
                cursor >= start &&
                cursor < end;
              const isSpoken = end !== null && end <= cursor;

              return (
                <span
                  key={`${line.id}-${index}`}
                  data-current-word={isCurrent ? "true" : undefined}
                  style={
                    line.technical
                      ? undefined
                      : isSpoken
                        ? {
                            color: layout.colorSpoken,
                            opacity: 0.7,
                          }
                        : isCurrent && layout.colorCurrent
                          ? {
                              backgroundColor: layout.colorCurrent,
                              color: layout.colorCurrentFg || undefined,
                            }
                          : undefined
                  }
                >
                  {word.display}
                  {index < line.words.length - 1 ? " " : ""}
                </span>
              );
            })}
          </span>
        </p>
      ))}
    </>
  );
}
