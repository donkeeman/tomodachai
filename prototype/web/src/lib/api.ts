// 프론트 공개 seam — 폴링/컴포넌트가 여기서 게임 런타임을 호출한다.
// 상태/영속/sim 오케스트레이션은 ./game(app 런타임)에 있고, 여기는 얇은 재노출.
export {
  getSnapshot,
  createCharacter,
  feed,
  give,
  answerBubble,
  saveGame,
  resetGame,
} from "./game";
export type { CreatePayload } from "./game";
