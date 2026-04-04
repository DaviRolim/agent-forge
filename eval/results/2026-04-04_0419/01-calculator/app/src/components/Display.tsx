"use client";

interface DisplayProps {
  expression: string;
  value: string;
  resultKey: number;
}

function getFontSize(value: string): string {
  const len = value.length;
  if (len <= 9) return "text-5xl";
  if (len <= 12) return "text-4xl";
  if (len <= 16) return "text-3xl";
  if (len <= 20) return "text-2xl";
  return "text-xl";
}

export default function Display({ expression, value, resultKey }: DisplayProps) {
  return (
    <div
      className="px-5 pt-6 pb-4 flex flex-col items-end justify-end min-h-[120px]"
      role="status"
      aria-live="polite"
      aria-label={`Display showing ${value}${expression ? `, expression: ${expression}` : ""}`}
    >
      <div
        className="text-sm text-slate-400 h-6 truncate w-full text-right font-medium tracking-wide"
        aria-label={expression ? `Expression: ${expression}` : "No expression"}
      >
        {expression || "\u00A0"}
      </div>
      <div
        key={resultKey}
        className={`${getFontSize(value)} font-bold text-white w-full text-right truncate animate-result tabular-nums`}
        aria-label={`Current value: ${value}`}
      >
        {value}
      </div>
    </div>
  );
}
