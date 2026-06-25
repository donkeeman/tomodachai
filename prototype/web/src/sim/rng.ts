// 시뮬레이션 확률 seam. Python simulation.py는 random.Random을 직접 쓰지만,
// 크로스-언어 비트일치(Mersenne Twister)는 목표가 아니다. RNG를 주입형
// 인터페이스로 추상화해 후처리/구조만 검증하고, 프로덕션 구현(Tauri)은 별도로 둔다.
//
// 의미론은 Python 표준 random 모듈을 미러:
//   random()        -> [0, 1) 실수
//   shuffle(arr)    -> in-place Fisher–Yates (random.shuffle)
//   choice(arr)     -> 단일 균등 선택 (빈 배열이면 구현이 throw)
//   sample(arr, k)  -> 비복원 k개 (random.sample; k>len이면 throw)
//   uniform(a, b)   -> [a, b] 실수 (random.uniform)

export interface SimRng {
  random(): number;
  shuffle<T>(arr: T[]): void;
  choice<T>(arr: readonly T[]): T;
  sample<T>(arr: readonly T[], k: number): T[];
  uniform(a: number, b: number): number;
}
