import { useEffect, useState } from "react";
import {
  DEFAULT_CURRENT_COLOR,
  DEFAULT_CURRENT_FG,
  DEFAULT_POINTER_COLOR,
  FONT_OPTIONS,
  type LayoutSection,
  type TeleprompterLayout,
  type TextAlign,
} from "../lib/teleprompterLayout";

type LayoutPopUpProps = {
  open: boolean;
  section: LayoutSection;
  value: TeleprompterLayout;
  onChange: (next: TeleprompterLayout) => void;
  onClose: () => void;
};

const SECTIONS: { id: LayoutSection; label: string }[] = [
  { id: "font", label: "Fonte" },
  { id: "fontSize", label: "Tamanho" },
  { id: "align", label: "Alinhamento" },
  { id: "colors", label: "Cores" },
];

const ALIGN_OPTIONS: { label: string; value: TextAlign }[] = [
  { label: "Esquerda", value: "left" },
  { label: "Centro", value: "center" },
  { label: "Direita", value: "right" },
];

export function LayoutPopUp({
  open,
  section,
  value,
  onChange,
  onClose,
}: LayoutPopUpProps) {
  const [activeSection, setActiveSection] = useState<LayoutSection>(section);
  const [draft, setDraft] = useState<TeleprompterLayout>(value);

  useEffect(() => {
    if (!open) return;
    setActiveSection(section);
    setDraft(value);
  }, [open, section, value]);

  if (!open) return null;

  function patch(partial: Partial<TeleprompterLayout>) {
    setDraft((current) => ({ ...current, ...partial }));
  }

  function save() {
    onChange(draft);
    onClose();
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="layout-settings-title"
      className="fixed inset-0 z-[9999] flex items-center justify-center overflow-y-auto bg-black/60 p-3 sm:p-6"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="flex max-h-[90dvh] w-full max-w-xl flex-col overflow-hidden rounded-xl bg-bg_white text-w_font shadow-2xl dark:bg-bg_dark dark:text-d_font"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="shrink-0 border-b border-current/15 px-5 py-4 sm:px-6">
          <h2 id="layout-settings-title" className="text-lg font-semibold">
            Layout do teleprompter
          </h2>
          <p className="mt-2 text-sm opacity-80">
            Ajuste fonte, tamanho, alinhamento e cores do texto.
          </p>
        </header>

        <div className="flex shrink-0 gap-1 overflow-x-auto border-b border-current/15 px-3 py-2">
          {SECTIONS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`rounded-md px-3 py-1.5 text-sm ${
                activeSection === item.id
                  ? "bg-w_font text-bg_white dark:bg-d_font dark:text-bg_dark"
                  : "hover:bg-black/5 dark:hover:bg-white/10"
              }`}
              onClick={() => setActiveSection(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4 sm:px-6">
          {activeSection === "font" && (
            <label className="flex flex-col gap-1.5 text-sm">
              <span>Tipo de fonte</span>
              <select
                className="rounded-md border border-current/25 bg-transparent px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                value={draft.fontFamily}
                onChange={(event) => patch({ fontFamily: event.target.value })}
              >
                {FONT_OPTIONS.map((option) => (
                  <option
                    key={option.label}
                    value={option.value}
                    className="bg-white text-gray-900 dark:bg-gray-800 dark:text-gray-100"
                  >
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          )}

          {activeSection === "fontSize" && (
            <label className="flex flex-col gap-1.5 text-sm">
              <span>Tamanho da fonte (px)</span>
              <input
                type="number"
                min={12}
                max={96}
                className="rounded-md border border-current/25 bg-transparent px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                value={draft.fontSizePx}
                onChange={(event) =>
                  patch({
                    fontSizePx: Number(event.target.value) || draft.fontSizePx,
                  })
                }
              />
            </label>
          )}

          {activeSection === "align" && (
            <fieldset className="flex flex-col gap-2 text-sm">
              <legend>Alinhamento do texto</legend>
              {ALIGN_OPTIONS.map((option) => (
                <label key={option.value} className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="text-align"
                    checked={draft.textAlign === option.value}
                    onChange={() => patch({ textAlign: option.value })}
                  />
                  {option.label}
                </label>
              ))}
            </fieldset>
          )}

          {activeSection === "colors" && (
            <div className="grid gap-4 text-sm sm:grid-cols-2">
              <label className="flex flex-col gap-1.5">
                <span>Texto normal</span>
                <input
                  type="color"
                  className="h-10 w-full cursor-pointer rounded-md border border-current/25 bg-transparent"
                  value={draft.colorNormal || "#16171d"}
                  onChange={(event) =>
                    patch({ colorNormal: event.target.value })
                  }
                />
                <button
                  type="button"
                  className="text-left text-xs opacity-70 underline"
                  onClick={() => patch({ colorNormal: "" })}
                >
                  Usar cor do tema (padrão)
                </button>
              </label>

              <label className="flex flex-col gap-1.5">
                <span>Marca-texto (fundo)</span>
                <input
                  type="color"
                  className="h-10 w-full cursor-pointer rounded-md border border-current/25 bg-transparent"
                  value={draft.colorCurrent || DEFAULT_CURRENT_COLOR}
                  onChange={(event) =>
                    patch({
                      colorCurrent: event.target.value,
                      colorCurrentFg:
                        draft.colorCurrentFg || DEFAULT_CURRENT_FG,
                    })
                  }
                />
                {draft.colorCurrent ? (
                  <button
                    type="button"
                    className="text-left text-xs opacity-70 underline"
                    onClick={() => patch({ colorCurrent: "" })}
                  >
                    Ocultar marca-texto
                  </button>
                ) : (
                  <p className="text-xs opacity-70">Marca-texto oculto</p>
                )}
              </label>

              <label
                className={`flex flex-col gap-1.5 ${
                  draft.colorCurrent ? "" : "opacity-50"
                }`}
              >
                <span>Marca-texto (texto)</span>
                <input
                  type="color"
                  disabled={!draft.colorCurrent}
                  className="h-10 w-full cursor-pointer rounded-md border border-current/25 bg-transparent disabled:cursor-not-allowed"
                  value={draft.colorCurrentFg || DEFAULT_CURRENT_FG}
                  onChange={(event) =>
                    patch({ colorCurrentFg: event.target.value })
                  }
                />
              </label>

              <label className="flex flex-col gap-1.5">
                <span>Texto já falado</span>
                <input
                  type="color"
                  className="h-10 w-full cursor-pointer rounded-md border border-current/25 bg-transparent"
                  value={draft.colorSpoken}
                  onChange={(event) =>
                    patch({ colorSpoken: event.target.value })
                  }
                />
              </label>

              <label className="flex flex-col gap-1.5">
                <span>Ponteiro (seta)</span>
                <input
                  type="color"
                  className="h-10 w-full cursor-pointer rounded-md border border-current/25 bg-transparent"
                  value={draft.pointerColor || DEFAULT_POINTER_COLOR}
                  onChange={(event) =>
                    patch({ pointerColor: event.target.value })
                  }
                />
                {draft.pointerColor ? (
                  <button
                    type="button"
                    className="text-left text-xs opacity-70 underline"
                    onClick={() => patch({ pointerColor: "" })}
                  >
                    Ocultar ponteiro
                  </button>
                ) : (
                  <p className="text-xs opacity-70">Ponteiro oculto</p>
                )}
              </label>
            </div>
          )}
        </div>

        <footer className="flex shrink-0 flex-wrap justify-end gap-2 border-t border-current/15 px-5 py-4 sm:px-6">
          <button
            type="button"
            className="rounded-md border border-current/25 px-3 py-2 text-sm hover:bg-black/5 dark:hover:bg-white/10"
            onClick={onClose}
          >
            Cancelar
          </button>
          <button
            type="button"
            className="rounded-md bg-w_font px-4 py-2 text-sm font-medium text-bg_white hover:opacity-80 dark:bg-d_font dark:text-bg_dark"
            onClick={save}
          >
            Salvar
          </button>
        </footer>
      </section>
    </div>
  );
}
