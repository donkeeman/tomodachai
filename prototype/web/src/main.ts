import "pretendard/dist/web/static/pretendard-dynamic-subset.css"; // 본문 폰트(OFL-1.1, 동적 서브셋)
import "./styles.css";
import { mount } from "svelte";
import App from "./App.svelte";
import { errorMsg } from "./lib/store";

// JS 오류를 화면 배너 스토어로 노출 (디버깅용)
window.addEventListener("error", (e) => {
  errorMsg.set("JS 오류: " + e.message + " @" + (e.filename || "") + ":" + (e.lineno || ""));
});
window.addEventListener("unhandledrejection", (e) => {
  const r: any = (e as PromiseRejectionEvent).reason;
  errorMsg.set("Promise 오류: " + ((r && r.message) || r));
});

const app = mount(App, { target: document.getElementById("app")! });
export default app;
