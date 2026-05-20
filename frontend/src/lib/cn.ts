import clsx, { type ClassValue } from "clsx";

export function cn(...args: ClassValue[]) {
  return clsx(...args);
}

export async function copy(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

export function scorePercent(score: number): number {
  return Math.round(Math.max(0, Math.min(1, score)) * 100);
}

export function scoreTier(score: number): "high" | "mid" | "low" | "weak" {
  if (score >= 0.8) return "high";
  if (score >= 0.5) return "mid";
  if (score >= 0.3) return "low";
  return "weak";
}
