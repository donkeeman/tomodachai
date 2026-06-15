import { writable } from "svelte/store";
import type { Snapshot, EventItem } from "./types";

// 서버 스냅샷 + 파생 UI 상태. 3D(village.ts)와 패널(컴포넌트)이 같은 스토어를 공유.
export const snapshot = writable<Snapshot | null>(null);
export const logItems = writable<EventItem[]>([]);
export const toastMsg = writable<string>("");
export const selectedId = writable<number | null>(null);
export const cardMode = writable<"info" | "foods" | "tools">("info");
export const viewMode = writable<"village" | "interior">("village");
export const followName = writable<string | null>(null);
export const modelLoaded = writable<boolean>(false);
export const errorMsg = writable<string>("");
export const albumOpen = writable<boolean>(false);
export const boardOpen = writable<boolean>(false);

let toastTimer: ReturnType<typeof setTimeout> | null = null;
export function toast(text: string) {
  toastMsg.set(text);
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastMsg.set(""), 3400);
}
