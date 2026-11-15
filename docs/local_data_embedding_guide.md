# 로컬 데이터 정제 및 임베딩 관리

이 문서는 비공개 상담 원본을 **GitHub로 업로드하지 않고** 검색 후보를 검수한 뒤 저장형 임베딩을 만드는 방법을 설명한다. 기존 검색 화면과 평가 코드는 변경하지 않는다. 이 기능은 #5, #6의 로컬 처리 단계이며 실제 앱 연결은 별도의 통합 단계에서 진행한다.

## 입력과 전제

- Python 3.10 이상 및 기존 저장소의 `requirements.txt` 의존성을 사용한다.
- 입력은 승인된 사용 범위 안에서 로컬에 보관된 상담 원천과 분류 라벨의 ZIP 또는 비압축 TAR이다.
- `src/data/aihub_loader.py`와 `src/data/aihub_schema.py`가 읽을 수 있는 원본 구조를 전제한다. 암호화된 ZIP, 일부만 내려받은 ZIP 및 압축 TAR은 지원하지 않는다.
- `data/consult_codes.csv`의 `aihub_category` 값을 변경하지 않고 업무 유형을 연결한다.
- 원본과 처리 결과는 Git에 포함하지 않는다. 현재 저장소에서 `data/raw/`와 `data/embeddings/`가 Git 추적에서 제외되는지 반드시 확인한다. 기존에 추적된 파일은 `.gitignore`로 보호되지 않는다.

## 1. 검수 후보 추출

저장소 루트의 Windows PowerShell에서 실행한다.

```powershell
$source = (Read-Host '상담 원천 ZIP/TAR의 실제 전체 경로').Trim('"')
$labels = (Read-Host '상담 분류 ZIP/TAR의 실제 전체 경로').Trim('"')
python -m src.data.prepare_questions --sources $source --labels $labels
```

결과 파일은 로컬의 `data/raw/question_twin/` 안에만 생성된다.

- `review_candidates.csv`: 후보 키, 요청 문장, 상담 코드, `needs_manual_review` 상태
- `approval_template.csv`: 후보 키와 빈 `approved_question` 입력란
- `review_report.json`: 원본·연결·보류·후보 건수의 집계

추출 후보는 검수 전 데이터다. 사람이 의미 적합성, 문맥, 복수 요청, 개인정보와 이용 권한을 확인해야 한다. 정규식 검사는 개인정보 부재를 보증하지 않는다.

## 2. 검수 후 정제 CSV 생성

`review_candidates.csv`의 후보와 같은 키를 가진 `approval_template.csv`의 `approved_question` 칸에 검수한 질문을 직접 기입한다. 보류할 후보는 빈칸 그대로 둔다. 필요한 경우 실제 개인식별 표현을 제외한 질문으로 다시 작성한다. 상담 코드·후보 키는 임의 변경하지 않는다.

```powershell
python -m src.data.prepare_questions --sources $source --labels $labels --approvals data/raw/question_twin/approval_template.csv
```

승인 결과는 `data/raw/question_twin/questions.csv`에 `id,question,category_code,duplicate_group,split` 열로 저장된다. 실데이터에는 중복 질문의 정답이나 평가 분할 정답이 없으므로 **마지막 두 열은 빈칸**이다. `eval/check_data.py`의 샘플 정답 검수 대상으로 사용하면 안 된다.

동일한 내용을 재실행하면 기존 출력을 유지한다. 다른 결과가 이미 같은 경로에 존재하면 덮어쓰지 않고 중단한다. 별도 버전을 만들려면 `--questions-output`, `--report` 등으로 `data/raw/` 아래의 새 출력 경로를 지정한다.

## 3. CPU 임베딩 생성 및 저장

정제 CSV가 존재하고 검수 및 권한 확인을 마친 다음 실행한다.

```powershell
python -m src.embedding.store build --csv data/raw/question_twin/questions.csv
python -m src.embedding.store verify --csv data/raw/question_twin/questions.csv
```

기존 모델 캐시에 필요한 파일이 없다면 모델 다운로드를 명시적으로 허용할 때에만 `build` 명령 뒤에 `--allow-download`를 붙인다. 유료 API는 사용하지 않는다. 모델명과 revision은 현재 `src/search/search.py`에 정의된 값을 재사용한다.

저장 결과는 `data/embeddings/question_twin/minilm_index.npz`이며 `id`, `question`, `category_code`, 정규화된 384차원 벡터, 모델·입력 버전 메타데이터를 포함한다. 벡터와 저장된 질문도 비공개 데이터로 취급한다. 이미 존재하는 인덱스는 자동 덮어쓰지 않는다.

`SavedIndex.search(query, top_k=5, threshold=0.7)`를 사용하면 기존 검색 함수와 같은 키의 결과가 나온다. 이 코드는 아직 기존 앱 검색 함수를 자동으로 바꾸지 않는다.

## 4. 합성 테스트

```powershell
python -m unittest discover -s tests -p test_prepare_questions.py -v
python -m unittest discover -s tests -p test_embedding_store.py -v
python -m unittest discover -s tests -v
```

첫 두 명령은 모의 모델·합성 ZIP으로 동작하며 원본 데이터나 모델 다운로드가 필요하지 않다. 마지막 명령은 기존 팀 코드까지 포함한 전체 단위 테스트로서 설치된 환경에 따라 의존성 확인이 필요하다.

## 보안 및 평가 한계

- 저장된 질문과 벡터를 저장소, 공개 데모, Issue, PR, 외부 로그, 협업 채팅에 포함하지 않는다.
- 검수 여부와 이용 허가는 별개다. 원본 제공자의 허용 범위와 사용자 개인정보 조건을 확인한다.
- 같은 업무 유형 검색 비율은 의미가 같은 질문 검색의 정밀도와 다르다. 평가 결과를 혼용하지 않는다.
- 현재 앱은 합성 질문 30개를 메모리에서 인코딩한다. 저장형 인덱스를 실제 UI에 연결하는 일은 다른 기능과 입출력 협의 후 진행한다.
