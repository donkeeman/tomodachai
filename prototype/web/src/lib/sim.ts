// 폴링 오케스트레이션: 스냅샷을 받아 스토어 + 3D(village)에 반영.
import { getSnapshot } from "./api";
import { snapshot, logItems, toast } from "./store";
import { initVillage, loadModels, applySnapshot, playEvents } from "./village";

let cursor = 0, polling = false, firstPoll = true, knownConfess = 0;

export async function pollNow() {
  if (polling) return;
  polling = true;
  try {
    const snap = await getSnapshot(cursor);
    cursor = snap.seq;
    snapshot.set(snap);
    let fresh = snap.events;
    if (firstPoll) {
      firstPoll = false;
      logItems.set(fresh.slice(-10));     // 지난 기록은 로그로만
      fresh = fresh.slice(-1);            // 최근 1건만 3D 연출
    } else if (fresh.length) {
      logItems.update((arr) => [...arr, ...fresh].slice(-90));
    }
    applySnapshot(snap);
    playEvents(fresh);
    const confess = snap.bubbles.filter((b) => b.kind === "confess_request");
    if (confess.length > knownConfess) toast(`${confess[confess.length - 1].char}의 말풍선이 도착했어요!`);
    knownConfess = confess.length;
  } catch {
    /* 서버 기동 대기 */
  }
  polling = false;
}

export async function startSim(canvas: HTMLCanvasElement) {
  initVillage(canvas);
  await loadModels();
  await pollNow();
  setInterval(pollNow, 1500);
}
