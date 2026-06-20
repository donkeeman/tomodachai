// Python src/tomodachai/character.py 미러 (순수 데이터 모델 + 결정론 파생).

/** 생일 "MM-DD" → 한국어 별자리. 인식 실패 시 "". Python calculate_zodiac 1:1. */
export function calculateZodiac(birthday: string): string {
  if (!birthday) return "";
  const month = Number.parseInt(birthday.slice(0, 2), 10);
  const day = Number.parseInt(birthday.slice(3, 5), 10);
  if (Number.isNaN(month) || Number.isNaN(day)) return "";

  if ((month === 3 && day >= 21) || (month === 4 && day <= 19)) return "양자리";
  if ((month === 4 && day >= 20) || (month === 5 && day <= 20)) return "황소자리";
  if ((month === 5 && day >= 21) || (month === 6 && day <= 20)) return "쌍둥이자리";
  if ((month === 6 && day >= 21) || (month === 7 && day <= 22)) return "게자리";
  if ((month === 7 && day >= 23) || (month === 8 && day <= 22)) return "사자자리";
  if ((month === 8 && day >= 23) || (month === 9 && day <= 22)) return "처녀자리";
  if ((month === 9 && day >= 23) || (month === 10 && day <= 22)) return "천칭자리";
  if ((month === 10 && day >= 23) || (month === 11 && day <= 21)) return "전갈자리";
  if ((month === 11 && day >= 22) || (month === 12 && day <= 21)) return "사수자리";
  if ((month === 12 && day >= 22) || (month === 1 && day <= 19)) return "염소자리";
  if ((month === 1 && day >= 20) || (month === 2 && day <= 18)) return "물병자리";
  if ((month === 2 && day >= 19) || (month === 3 && day <= 20)) return "물고기자리";
  return "";
}
