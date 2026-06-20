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

export type Msg = { role: "system" | "user" | "assistant"; content: string };
export type ChatOpts = {
  temperature?: number;
  maxTokens?: number;
  apiBase?: string;
  model?: string;
};

const DEFAULTS = {
  apiBase: "http://localhost:11434",
  model: "llama3.1",
  temperature: 0.8,
  maxTokens: 512,
};

function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

// 패키징(Tauri)에선 플러그인 fetch(CORS 우회), dev 브라우저/노드에선 전역 fetch.
async function httpFetch(url: string, init: RequestInit): Promise<Response> {
  if (isTauri()) {
    const { fetch: tauriFetch } = await import("@tauri-apps/plugin-http");
    return tauriFetch(url, init) as unknown as Response;
  }
  return globalThis.fetch(url, init);
}

export async function chat(messages: Msg[], opts: ChatOpts = {}): Promise<string> {
  const apiBase = opts.apiBase ?? DEFAULTS.apiBase;
  const body = {
    model: opts.model ?? DEFAULTS.model,
    messages,
    stream: false,
    options: {
      temperature: opts.temperature ?? DEFAULTS.temperature,
      num_predict: opts.maxTokens ?? DEFAULTS.maxTokens,
    },
  };
  const res = await httpFetch(`${apiBase}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Ollama 응답 오류: ${res.status}`);
  const data = (await res.json()) as { message?: { content?: string } };
  return data.message?.content ?? "";
}

export async function chatJson(
  messages: Msg[],
  opts: ChatOpts & { retries?: number } = {},
): Promise<Record<string, unknown>> {
  const retries = opts.retries ?? 2;
  let lastErr: unknown = null;
  let content = "";
  for (let attempt = 0; attempt <= retries; attempt++) {
    content = await chat(messages, opts);
    try {
      return parseJson(content);
    } catch (e) {
      lastErr = e;
    }
  }
  throw new Error(`JSON 파싱 실패 (${retries + 1}회 시도): ${lastErr}\n응답: ${content.slice(0, 500)}`);
}
