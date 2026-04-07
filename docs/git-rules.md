# Git 작업 규칙

## Force Push 금지 (원칙)
- force push 전에 **반드시** `git fetch origin` + `git log --oneline origin/main`으로 리모트 최신 상태 확인.
- 리모트에 이쪽에 없는 커밋이 있으면 merge/rebase 먼저. 없을 때만 force push.
- **사유:** 다른 컴퓨터에서 작업한 커밋이 리모트에 있었는데, pull 없이 force push하여 덮어씌운 사고 발생 (2026-04-07).

## 커밋 계정
- 이 레포는 `donkeeman <doonkeeemaan@gmail.com>` 계정으로 커밋.
- SSH: `git@github-donkeeman:donkeeman/tomodachai.git`
