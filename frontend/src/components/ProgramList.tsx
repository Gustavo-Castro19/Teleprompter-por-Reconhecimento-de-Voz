import type { RetrancaMarker } from "../lib/scriptModel";

type ProgramListProps = {
  markers: RetrancaMarker[];
  selectedId: string | null;
  onSelect: (marker: RetrancaMarker) => void;
  onSelectStart: () => void;
};

export function ProgramList({
  markers,
  selectedId,
  onSelect,
  onSelectStart,
}: ProgramListProps) {
  const atStart = selectedId === null;

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-current/20">
      <header className="border-b border-current/15 px-4 py-3">
        <h2 className="text-sm font-semibold">Retrancas</h2>
        <p className="mt-1 text-xs opacity-70">
          Salte para um tema do roteiro (RETRANCA).
        </p>
      </header>

      <div className="scrollbar-sm min-h-0 flex-1 overflow-y-auto p-2">
        {markers.length === 0 ? (
          <p className="px-2 py-6 text-center text-sm opacity-70">
            Nenhuma retranca. Importe um roteiro em File.
          </p>
        ) : (
          <ul className="flex flex-col gap-1">
            <li>
              <button
                type="button"
                className={`w-full rounded-md px-3 py-2 text-left text-sm ${
                  atStart
                    ? "bg-w_font text-bg_white dark:bg-d_font dark:text-bg_dark"
                    : "hover:bg-black/5 dark:hover:bg-white/10"
                }`}
                aria-current={atStart ? "true" : undefined}
                onClick={onSelectStart}
              >
                <span className="block truncate font-medium">
                  Início do roteiro
                </span>
                <span className="block text-xs opacity-70">
                  Acompanhar desde o começo
                </span>
              </button>
            </li>

            {markers.map((marker) => {
              const selected = marker.id === selectedId;
              const pg = marker.pg_index?.trim();

              return (
                <li key={marker.id}>
                  <button
                    type="button"
                    className={`w-full rounded-md px-3 py-2 text-left text-sm ${
                      selected
                        ? "bg-w_font text-bg_white dark:bg-d_font dark:text-bg_dark"
                        : "hover:bg-black/5 dark:hover:bg-white/10"
                    }`}
                    aria-current={selected ? "true" : undefined}
                    onClick={() => onSelect(marker)}
                  >
                    <span className="block truncate font-medium">
                      {marker.title}
                    </span>
                    <span className="block text-xs opacity-70">
                      {pg ? `PG ${pg}` : "Salto no roteiro"}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </aside>
  );
}
