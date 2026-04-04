"use client";

import { useCallback } from "react";

type BtnType = "digit" | "operator" | "function" | "equals";

interface BtnDef {
  label: string;
  type: BtnType;
  action: string;
  gridArea: string;
}

// 6-row × 4-column grid:
// Row 1: AC   C    ⌫    ÷
// Row 2: 7    8    9    ×
// Row 3: 4    5    6    -
// Row 4: 1    2    3    +
// Row 5: +/-  %    .    = (spans row 5–6)
// Row 6: 0 (spans col 1–3)  = (continued)
const BUTTONS: BtnDef[] = [
  { label: "AC",  type: "function", action: "allClear",   gridArea: "1 / 1 / 2 / 2" },
  { label: "C",   type: "function", action: "clearEntry",  gridArea: "1 / 2 / 2 / 3" },
  { label: "⌫",   type: "function", action: "backspace",   gridArea: "1 / 3 / 2 / 4" },
  { label: "÷",   type: "operator", action: "÷",           gridArea: "1 / 4 / 2 / 5" },

  { label: "7",   type: "digit",    action: "7",           gridArea: "2 / 1 / 3 / 2" },
  { label: "8",   type: "digit",    action: "8",           gridArea: "2 / 2 / 3 / 3" },
  { label: "9",   type: "digit",    action: "9",           gridArea: "2 / 3 / 3 / 4" },
  { label: "×",   type: "operator", action: "×",           gridArea: "2 / 4 / 3 / 5" },

  { label: "4",   type: "digit",    action: "4",           gridArea: "3 / 1 / 4 / 2" },
  { label: "5",   type: "digit",    action: "5",           gridArea: "3 / 2 / 4 / 3" },
  { label: "6",   type: "digit",    action: "6",           gridArea: "3 / 3 / 4 / 4" },
  { label: "-",   type: "operator", action: "-",           gridArea: "3 / 4 / 4 / 5" },

  { label: "1",   type: "digit",    action: "1",           gridArea: "4 / 1 / 5 / 2" },
  { label: "2",   type: "digit",    action: "2",           gridArea: "4 / 2 / 5 / 3" },
  { label: "3",   type: "digit",    action: "3",           gridArea: "4 / 3 / 5 / 4" },
  { label: "+",   type: "operator", action: "+",           gridArea: "4 / 4 / 5 / 5" },

  { label: "+/−", type: "function", action: "toggleSign",  gridArea: "5 / 1 / 6 / 2" },
  { label: "%",   type: "function", action: "percent",     gridArea: "5 / 2 / 6 / 3" },
  { label: ".",   type: "digit",    action: ".",            gridArea: "5 / 3 / 6 / 4" },

  { label: "0",   type: "digit",    action: "0",           gridArea: "6 / 1 / 7 / 4" },

  // = spans two rows (row 5–6), col 4
  { label: "=",   type: "equals",   action: "equals",      gridArea: "5 / 4 / 7 / 5" },
];

export const KEYBOARD_TO_BUTTON: Record<string, string> = {
  "0": "0", "1": "1", "2": "2", "3": "3", "4": "4",
  "5": "5", "6": "6", "7": "7", "8": "8", "9": "9",
  "+": "+", "-": "-", "*": "×", x: "×", "/": "÷",
  ".": ".", Enter: "=", "=": "=", Escape: "AC", Backspace: "⌫", "%": "%",
};

interface ButtonGridProps {
  onDigit: (d: string) => void;
  onOperator: (op: string) => void;
  onEquals: () => void;
  onAllClear: () => void;
  onClearEntry: () => void;
  onBackspace: () => void;
  onPercent: () => void;
  onToggleSign: () => void;
  onDecimal: () => void;
  activeKey: string | null;
}

function btnClasses(type: BtnType): string {
  const base =
    "rounded-xl font-semibold transition-all duration-150 ease-out cursor-pointer select-none focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-offset-1 focus-visible:ring-offset-slate-900";
  switch (type) {
    case "digit":
      return `${base} bg-slate-700 text-slate-100 hover:bg-slate-600 active:scale-[0.95] active:bg-slate-500`;
    case "operator":
      return `${base} bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 active:scale-[0.95] active:bg-amber-500/40 text-lg`;
    case "function":
      return `${base} bg-slate-500/40 text-slate-200 hover:bg-slate-500/60 active:scale-[0.95] active:bg-slate-400/50`;
    case "equals":
      return `${base} bg-amber-500 text-slate-900 hover:bg-amber-400 active:scale-[0.95] active:bg-amber-300 font-bold text-2xl`;
  }
}

function ariaLabel(label: string): string {
  switch (label) {
    case "⌫": return "Backspace";
    case "+/−": return "Toggle sign";
    case "÷": return "Divide";
    case "×": return "Multiply";
    default: return label;
  }
}

export default function ButtonGrid({
  onDigit,
  onOperator,
  onEquals,
  onAllClear,
  onClearEntry,
  onBackspace,
  onPercent,
  onToggleSign,
  onDecimal,
  activeKey,
}: ButtonGridProps) {
  const handleClick = useCallback(
    (btn: BtnDef) => {
      switch (btn.action) {
        case "allClear": onAllClear(); break;
        case "clearEntry": onClearEntry(); break;
        case "backspace": onBackspace(); break;
        case "percent": onPercent(); break;
        case "toggleSign": onToggleSign(); break;
        case "equals": onEquals(); break;
        case ".": onDecimal(); break;
        case "+": case "-": case "×": case "÷":
          onOperator(btn.action); break;
        default:
          onDigit(btn.action);
      }
    },
    [onDigit, onOperator, onEquals, onAllClear, onClearEntry, onBackspace, onPercent, onToggleSign, onDecimal]
  );

  return (
    <div
      className="grid grid-cols-4 gap-2.5 p-4"
      style={{ gridTemplateRows: "repeat(6, minmax(48px, 1fr))" }}
    >
      {BUTTONS.map((btn) => (
        <button
          key={btn.label}
          data-key={btn.label}
          onClick={() => handleClick(btn)}
          style={{ gridArea: btn.gridArea }}
          className={`${btnClasses(btn.type)} min-h-[48px] text-base ${
            activeKey === btn.label ? "scale-[0.95] brightness-125" : ""
          }`}
          aria-label={ariaLabel(btn.label)}
        >
          {btn.label}
        </button>
      ))}
    </div>
  );
}
