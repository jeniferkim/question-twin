# 표현이 다른 중복 질문 찾기

## 협업 규칙

### 작업 순서

1. 담당 Issue 확인
2. `dev`에서 브랜치 생성
3. 작업 후 커밋, push
4. `dev` 대상으로 PR 생성
5. 팀장 승인 후 merge

```bash
git switch dev
git pull origin dev
git switch -c feat/search-7
```

### 브랜치

`type/작업내용-이슈번호`

```text
feat/search-7
fix/embedding-load-21
docs/readme-17
```

### 커밋

`type: 작업 내용 (#이슈번호)`

```text
feat: 유사 질문 Top 5 검색 구현 (#7)
fix: 빈 질문 입력 오류 수정 (#21)
docs: 실행 방법 작성 (#17)
```

| type | 사용 시점 |
|---|---|
| `feat` | 기능, 데이터 처리, 모델, 평가 코드 추가 |
| `fix` | 버그 수정 |
| `docs` | README, 문서 수정 |
| `test` | 테스트 추가, 수정 |
| `refactor` | 동작 변경 없는 코드 개선 |
| `chore` | 설정, 패키지, 폴더 정리 |

- 메시지는 한글로 작성합니다.
- 커밋 하나에는 작업 하나만 담습니다.
- 본인 담당 코드는 본인 계정으로 커밋합니다.

### PR

- 제목: 커밋과 같은 형식
- 대상 브랜치: `dev`
- 본문: 작업 내용과 `Closes #이슈번호`
- merge: 팀장 승인 후 팀장이 진행
- `main`에는 직접 push하지 않습니다.