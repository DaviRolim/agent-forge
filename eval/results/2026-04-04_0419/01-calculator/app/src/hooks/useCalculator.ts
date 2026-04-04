"use client";

import { useState, useCallback } from "react";

export interface HistoryEntry {
  expression: string;
  result: string;
}

interface CalculatorState {
  display: string;
  expression: string;
  accumulator: number | null;
  pendingOperator: string | null;
  waitingForOperand: boolean;
  justEvaluated: boolean;
  error: boolean;
  hasInput: boolean;
}

const INITIAL_STATE: CalculatorState = {
  display: "0",
  expression: "",
  accumulator: null,
  pendingOperator: null,
  waitingForOperand: false,
  justEvaluated: false,
  error: false,
  hasInput: false,
};

function formatNumber(n: number): string {
  if (!isFinite(n) || isNaN(n)) return "Error";
  const rounded = parseFloat(n.toPrecision(12));
  return String(rounded);
}

function compute(left: number, operator: string, right: number): number {
  switch (operator) {
    case "+":
      return left + right;
    case "-":
      return left - right;
    case "×":
      return left * right;
    case "÷":
      return right === 0 ? NaN : left / right;
    default:
      return right;
  }
}

const DISPLAY_OP: Record<string, string> = {
  "+": "+",
  "-": "-",
  "*": "×",
  "×": "×",
  x: "×",
  "/": "÷",
  "÷": "÷",
};

export function useCalculator() {
  const [state, setState] = useState<CalculatorState>(INITIAL_STATE);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [resultKey, setResultKey] = useState(0);

  const inputDigit = useCallback((digit: string) => {
    setState((prev) => {
      if (prev.error) {
        return { ...INITIAL_STATE, display: digit, hasInput: true };
      }
      if (prev.justEvaluated) {
        return {
          ...INITIAL_STATE,
          display: digit,
          hasInput: true,
        };
      }
      if (prev.waitingForOperand) {
        return {
          ...prev,
          display: digit,
          waitingForOperand: false,
          hasInput: true,
        };
      }
      const newDisplay = prev.display === "0" ? digit : prev.display + digit;
      return { ...prev, display: newDisplay, hasInput: true };
    });
  }, []);

  const inputDecimal = useCallback(() => {
    setState((prev) => {
      if (prev.error) {
        return { ...INITIAL_STATE, display: "0.", hasInput: true };
      }
      if (prev.justEvaluated) {
        return { ...INITIAL_STATE, display: "0.", hasInput: true };
      }
      if (prev.waitingForOperand) {
        return {
          ...prev,
          display: "0.",
          waitingForOperand: false,
          hasInput: true,
        };
      }
      if (prev.display.includes(".")) return prev;
      return { ...prev, display: prev.display + ".", hasInput: true };
    });
  }, []);

  const inputOperator = useCallback((op: string) => {
    const displayOp = DISPLAY_OP[op] || op;

    setState((prev) => {
      if (prev.error) return prev;

      const inputValue = parseFloat(prev.display);

      if (!prev.hasInput && prev.accumulator === null && !prev.justEvaluated && !prev.waitingForOperand) {
        return prev;
      }

      if (prev.justEvaluated) {
        return {
          ...prev,
          accumulator: inputValue,
          pendingOperator: displayOp,
          expression: `${prev.display} ${displayOp}`,
          waitingForOperand: true,
          justEvaluated: false,
        };
      }

      if (prev.waitingForOperand && prev.pendingOperator) {
        return {
          ...prev,
          pendingOperator: displayOp,
          expression: prev.expression.slice(0, -1) + displayOp,
        };
      }

      if (prev.accumulator !== null && prev.pendingOperator && !prev.waitingForOperand) {
        const result = compute(prev.accumulator, prev.pendingOperator, inputValue);
        if (isNaN(result) || !isFinite(result)) {
          return {
            ...prev,
            display: "Error",
            error: true,
            accumulator: null,
            pendingOperator: null,
            expression: "",
            waitingForOperand: false,
          };
        }
        const formatted = formatNumber(result);
        return {
          ...prev,
          display: formatted,
          accumulator: result,
          pendingOperator: displayOp,
          expression: `${formatted} ${displayOp}`,
          waitingForOperand: true,
        };
      }

      return {
        ...prev,
        accumulator: inputValue,
        pendingOperator: displayOp,
        expression: `${prev.display} ${displayOp}`,
        waitingForOperand: true,
      };
    });
  }, []);

  const evaluate = useCallback(() => {
    setState((prev) => {
      if (prev.error) return prev;
      if (prev.accumulator === null || !prev.pendingOperator) return prev;
      if (prev.waitingForOperand) return prev;

      const inputValue = parseFloat(prev.display);
      const result = compute(prev.accumulator, prev.pendingOperator, inputValue);

      const fullExpression = `${prev.expression} ${prev.display}`;

      if (isNaN(result) || !isFinite(result)) {
        setHistory((h) => {
          const entry: HistoryEntry = {
            expression: fullExpression,
            result: "Error",
          };
          return [entry, ...h].slice(0, 10);
        });
        return {
          ...prev,
          display: "Error",
          error: true,
          accumulator: null,
          pendingOperator: null,
          expression: "",
          waitingForOperand: false,
          justEvaluated: false,
        };
      }

      const formatted = formatNumber(result);
      setHistory((h) => {
        const entry: HistoryEntry = {
          expression: fullExpression,
          result: formatted,
        };
        return [entry, ...h].slice(0, 10);
      });
      setResultKey((k) => k + 1);

      return {
        display: formatted,
        expression: "",
        accumulator: null,
        pendingOperator: null,
        waitingForOperand: false,
        justEvaluated: true,
        error: false,
        hasInput: false,
      };
    });
  }, []);

  const clearEntry = useCallback(() => {
    setState((prev) => {
      if (prev.error) return INITIAL_STATE;
      return {
        ...prev,
        display: "0",
        waitingForOperand: prev.pendingOperator !== null,
        justEvaluated: false,
      };
    });
  }, []);

  const allClear = useCallback(() => {
    setState(INITIAL_STATE);
  }, []);

  const backspace = useCallback(() => {
    setState((prev) => {
      if (prev.error) return INITIAL_STATE;
      if (prev.justEvaluated) return prev;
      if (prev.waitingForOperand) return prev;
      const newDisplay =
        prev.display.length > 1 ? prev.display.slice(0, -1) : "0";
      return { ...prev, display: newDisplay };
    });
  }, []);

  const percent = useCallback(() => {
    setState((prev) => {
      if (prev.error) return prev;
      const value = parseFloat(prev.display);
      const result = value / 100;
      return {
        ...prev,
        display: formatNumber(result),
        justEvaluated: false,
      };
    });
  }, []);

  const toggleSign = useCallback(() => {
    setState((prev) => {
      if (prev.error) return prev;
      if (prev.display === "0") return prev;
      const newDisplay = prev.display.startsWith("-")
        ? prev.display.slice(1)
        : "-" + prev.display;
      return { ...prev, display: newDisplay };
    });
  }, []);

  const loadFromHistory = useCallback((result: string) => {
    if (result === "Error") return;
    setState({
      ...INITIAL_STATE,
      display: result,
      justEvaluated: true,
    });
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
  }, []);

  return {
    display: state.display,
    expression: state.expression,
    error: state.error,
    resultKey,
    history,
    inputDigit,
    inputDecimal,
    inputOperator,
    evaluate,
    clearEntry,
    allClear,
    backspace,
    percent,
    toggleSign,
    loadFromHistory,
    clearHistory,
  };
}
