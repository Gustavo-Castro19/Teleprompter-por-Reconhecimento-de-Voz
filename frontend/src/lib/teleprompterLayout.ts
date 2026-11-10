export type TextAlign = "left" | "center" | "right";

export type LayoutSection = "font" | "fontSize" | "align" | "colors";

export type TeleprompterLayout = {
  fontFamily: string;
  fontSizePx: number;
  textAlign: TextAlign;
  colorNormal: string;
  /** Fundo do marca-texto da palavra atual; string vazia oculta o marcador. */
  colorCurrent: string;
  colorCurrentFg: string;
  colorSpoken: string;
  /** Cor da seta-ponteiro; string vazia oculta o ponteiro. */
  pointerColor: string;
};

export const LAYOUT_STORAGE_KEY = "teleprompter-layout";

/** Fundo padrão do marca-texto da palavra atual. */
export const DEFAULT_CURRENT_COLOR = "#fcd34d";
/** Texto padrão sobre o marca-texto. */
export const DEFAULT_CURRENT_FG = "#000000";
/** Vermelho padrão da seta (equiv. text-red-600). */
export const DEFAULT_POINTER_COLOR = "#dc2626";

export const DEFAULT_LAYOUT: TeleprompterLayout = {
  fontFamily: "Arial, Helvetica, sans-serif",
  fontSizePx: 72,
  textAlign: "left",
  colorNormal: "",
  colorCurrent: DEFAULT_CURRENT_COLOR,
  colorCurrentFg: DEFAULT_CURRENT_FG,
  colorSpoken: "#047857",
  pointerColor: DEFAULT_POINTER_COLOR,
};

export const FONT_OPTIONS: { label: string; value: string }[] = [
  { label: "Padrão do sistema", value: "" },
  { label: "Arial", value: "Arial, Helvetica, sans-serif" },
  { label: "Georgia", value: "Georgia, serif" },
  { label: "Times New Roman", value: '"Times New Roman", Times, serif' },
  { label: "Courier New", value: '"Courier New", Courier, monospace' },
  { label: "Verdana", value: "Verdana, Geneva, sans-serif" },
  { label: "system-ui", value: "system-ui, sans-serif" },
];

export function loadTeleprompterLayout(): TeleprompterLayout {
  try {
    const raw = localStorage.getItem(LAYOUT_STORAGE_KEY);
    if (!raw) return { ...DEFAULT_LAYOUT };
    const parsed = JSON.parse(raw) as Partial<TeleprompterLayout>;
    return { ...DEFAULT_LAYOUT, ...parsed };
  } catch {
    return { ...DEFAULT_LAYOUT };
  }
}

export function saveTeleprompterLayout(layout: TeleprompterLayout): void {
  localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(layout));
}
