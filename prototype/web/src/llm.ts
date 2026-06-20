// Python src/tomodachai/llm.py 의 LLMClient 미러 (Ollama 직통 seam).

/** LLM 응답 문자열에서 JSON 추출. Python _parse_json 1:1 포팅(순수, 결정론). */
export function parseJson(text: string): Record<string, unknown> {
  const t = text.trim();
  if (!t) throw new Error("빈 응답");
  // 마크다운 코드블록 안의 JSON (non-greedy, DOTALL 동등)
  const fence = t.match(/```(?:json)?\s*\n?([\s\S]*?)```/);
  if (fence) return JSON.parse(fence[1].trim());
  // 첫 { ... } 블록 (greedy, DOTALL 동등)
  const brace = t.match(/\{[\s\S]*\}/);
  if (brace) return JSON.parse(brace[0]);
  return JSON.parse(t);
}
