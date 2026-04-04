"use client";

import { useEffect, useState, useCallback } from "react";
import { useCalculator } from "@/hooks/useCalculator";
import Display from "./Display";
import ButtonGrid, { KEYBOARD_TO_BUTTON } from "./ButtonGrid";
import HistoryPanel from "./HistoryPanel";

export default function Calculator() {
  const calc = useCalculator();
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  const dispatchAction = useCallback(
    (buttonLabel: string) => {
      switch (buttonLabel) {
        case "0": case "1": case "2": case "3": case "4":
        case "5": case "6": case "7": case "8": case "9":
          calc.inputDigit(buttonLabel);
          break;
        case ".":
          calc.inputDecimal();
          break;
        case "+": case "-": case "×": case "÷":
          calc.inputOperator(buttonLabel);
          break;
        case "=":
          calc.evaluate();
          break;
        case "AC":
          calc.allClear();
          break;
        case "⌫":
          calc.backspace();
          break;
        case "%":
          calc.percent();
          break;
      }
    },
    [calc]
  );

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return;

      const mapped = KEYBOARD_TO_BUTTON[e.key];
      if (!mapped) return;

      e.preventDefault();
      setActiveKey(mapped);
      dispatchAction(mapped);
    };

    const handleKeyUp = () => {
      setActiveKey(null);
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [dispatchAction]);

  return (
    <div className="flex-1 flex items-center justify-center p-4">
      <div className="flex flex-col md:flex-row gap-4 w-full max-w-[800px]">
        {/* Calculator body */}
        <div className="w-full md:w-[380px] shrink-0 bg-slate-800 rounded-2xl shadow-2xl shadow-black/40 overflow-hidden">
          <Display
            expression={calc.expression}
            value={calc.display}
            resultKey={calc.resultKey}
          />
          <ButtonGrid
            onDigit={calc.inputDigit}
            onOperator={calc.inputOperator}
            onEquals={calc.evaluate}
            onAllClear={calc.allClear}
            onClearEntry={calc.clearEntry}
            onBackspace={calc.backspace}
            onPercent={calc.percent}
            onToggleSign={calc.toggleSign}
            onDecimal={calc.inputDecimal}
            activeKey={activeKey}
          />
        </div>

        {/* History — toggle button on mobile */}
        <button
          onClick={() => setShowHistory((v) => !v)}
          className="md:hidden text-sm text-slate-400 hover:text-slate-200 transition-colors py-2 cursor-pointer"
          aria-label="Toggle history panel"
        >
          {showHistory ? "Hide History" : "Show History"} ({calc.history.length})
        </button>

        {/* History panel — sidebar on desktop, collapsible on mobile */}
        <div
          className={`${
            showHistory ? "block" : "hidden"
          } md:block w-full md:w-[260px] bg-slate-800/60 rounded-2xl shadow-lg shadow-black/20 min-h-[200px] max-h-[500px] md:max-h-none md:h-auto overflow-hidden`}
        >
          <HistoryPanel
            history={calc.history}
            onSelect={calc.loadFromHistory}
            onClear={calc.clearHistory}
          />
        </div>
      </div>
    </div>
  );
}
