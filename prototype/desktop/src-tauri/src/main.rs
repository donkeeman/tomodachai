// 별빛 마을 — Tauri 데스크탑 셸 진입점.
// 시뮬레이션/렌더링은 모두 웹 프론트(파이썬 서버가 제공)에서 돌고,
// 여기서는 네이티브 창만 띄운다. (가벼운 데스크탑 상주 = OS 웹뷰)
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("Tauri 앱 실행 중 오류");
}
