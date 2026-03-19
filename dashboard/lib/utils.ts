import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function parseJson<T>(value: string | null | undefined, fallback: T): T {
  if (!value) return fallback;

  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

export function avatarUrl(discordId: string, avatar?: string | null) {
  if (!avatar) return null;
  return `https://cdn.discordapp.com/avatars/${discordId}/${avatar}.png`;
}

export function truncate(value: string, length = 80) {
  return value.length > length ? `${value.slice(0, length)}…` : value;
}
