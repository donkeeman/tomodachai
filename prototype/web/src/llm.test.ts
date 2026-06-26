import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { parseJson } from "./llm";
import { chat, chatJson } from "./llm";
import { loadGolden } from "./sim/__golden__/loadGolden";

describe("parseJson (golden vs Python _parse_json)", () => {
  const cases = loadGolden<string, Record<string, unknown>>("parse_json");
  it.each(cases)("input %# matches Python", (c) => {
    if (c.throws) {
      expect(() => parseJson(c.input)).toThrow();
    } else {
      expect(parseJson(c.input)).toEqual(c.expected);
    }
  });
});

function ollamaReply(content: string) {
  return { ok: true, json: async () => ({ message: { content } }) } as unknown as Response;
}

describe("chat / chatJson (mocked fetch)", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("chat returns Ollama message content", async () => {
    (globalThis.fetch as any).mockResolvedValueOnce(ollamaReply("안녕"));
    await expect(chat([{ role: "user", content: "hi" }])).resolves.toBe("안녕");
  });

  it("chatJson retries on bad JSON then succeeds (retries=2 → 2 calls)", async () => {
    (globalThis.fetch as any)
      .mockResolvedValueOnce(ollamaReply("not json"))
      .mockResolvedValueOnce(ollamaReply('{"ok": true}'));
    await expect(chatJson([{ role: "user", content: "hi" }])).resolves.toEqual({ ok: true });
    expect((globalThis.fetch as any).mock.calls.length).toBe(2);
  });

  it("chatJson throws after exhausting retries (3 calls)", async () => {
    (globalThis.fetch as any).mockResolvedValue(ollamaReply("nope"));
    await expect(chatJson([{ role: "user", content: "hi" }])).rejects.toThrow();
    expect((globalThis.fetch as any).mock.calls.length).toBe(3);
  });
});
