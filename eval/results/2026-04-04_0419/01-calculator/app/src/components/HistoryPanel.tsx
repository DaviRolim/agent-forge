"use client";

import { HistoryEntry } from "@/hooks/useCalculator";

interface HistoryPanelProps {
  history: HistoryEntry[];
  onSelect: (result: string) => void;
  onClear: () => void;
}

export default function HistoryPanel({
  history,
  onSelect,
  onClear,
}: HistoryPanelProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/50">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          History
        </h2>
        {history.length > 0 && (
          <button
            onClick={onClear}
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors duration-150 cursor-pointer"
          >
            Clear History
          </button>
        )}
      </div>
      <div className="flex-1 overflow-y-auto px-2 py-2">
        {history.length === 0 ? (
          <p className="text-slate-600 text-sm text-center py-8">
            No calculations yet
          </p>
        ) : (
          <ul className="space-y-1">
            {history.map((entry, i) => (
              <li key={`${entry.expression}-${i}`}>
                <button
                  onClick={() => onSelect(entry.result)}
                  className="w-full text-right px-3 py-2.5 rounded-lg hover:bg-slate-700/50 transition-colors duration-150 cursor-pointer animate-slide-in"
                  aria-label={`Load result ${entry.result} from ${entry.expression}`}
                >
                  <div className="text-xs text-slate-500 truncate">
                    {entry.expression} =
                  </div>
                  <div className="text-sm font-semibold text-amber-400 tabular-nums">
                    {entry.result}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
