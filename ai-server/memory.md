# EXAONE 워크플로 신뢰성 작업 기록

최종 갱신: 2026-08-13
현재 작업 브랜치: `reviser-output-reliability`

## 사용자 결정

- 서버는 Python으로 계속 유지합니다.
- Python 내부 모델과 LLM 구조화 출력은 `snake_case`를 사용합니다.
- 과거 Java 내부 DTO 이름에 맞추기 위한 serialization/validation alias는 추가하지 않습니다.
- 다만 HTTP 요청/응답, 환경 변수처럼 실제 외부 계약에 필요한 기존 alias는 유지합니다.
- 이번 작업은 GitHub 이슈 없이 진행하고 변경 내역을 사용자에게 직접 보고합니다. PR과 커밋도 생성하지 않았습니다.

## EXAONE 조사 결과와 적용 원칙

- [K-EXAONE 공식 저장소](https://github.com/LG-AI-EXAONE/K-EXAONE)와 [기술 보고서](https://arxiv.org/abs/2601.01739)에 따르면 현재 모델은 총 236B/활성 23B MoE, 256K 컨텍스트 모델이며 reasoning/non-reasoning 모드를 구분합니다.
- [Friendli 모델 페이지](https://friendli.ai/models/LGAI-EXAONE/K-EXAONE-236B-A23B)의 OpenAI 호환 API와 `chat_template_kwargs.enable_thinking`을 사용합니다.
- [Friendli reasoning 문서](https://friendli.ai/docs/guides/reasoning)에 맞춰 reasoning 결과는 응답 본문에서 분리하고 숨겨도 사용 토큰에는 포함된다는 점을 비용 판단에 반영했습니다.
- [Friendli structured outputs 문서](https://friendli.ai/docs/guides/structured-outputs)에 따라 JSON 스키마는 형식만 강제하며 내용 품질은 프롬프트와 코드 검증이 담당하도록 설계했습니다.
- 복잡한 구조화 출력은 유효한 스키마여도 출력 토큰을 끝까지 소모할 수 있으므로, 큰 단일 스키마보다 작은 단계별 스키마를 사용합니다.

## 최종 설계 결정

1. Schemer
   - 정상 입력은 non-reasoning, temperature 0으로 한 번 검사합니다.
   - 최초 거절일 때만 원문 전체와 첫 거절 사유를 포함해 reasoning 모드로 한 번 독립 확인합니다.
   - 문법, 분량, 약한 근거, 직무 적합성 부족은 거절 사유가 아니며 이후 평가 항목으로 넘깁니다.
   - 두 번 모두 명백히 부적절할 때만 `InvalidSubmissionError`로 종료합니다.

2. WebSearch
   - non-reasoning 결정적 생성으로 한두 개의 집중된 검색 계획만 요청합니다.
   - 마지막 user 메시지를 비워 두지 않습니다.
   - `tool_type`은 Python `Literal["web_search"]`이며 Java용 alias를 두지 않습니다.

3. Evaluate
   - 전체 평가 기준은 첫 axes 단계에 한 번만 전달합니다.
   - 출력은 `axes → fit → improvement_summary → improvement_strategy` 네 개의 작은 스키마로 나눕니다.
   - 후속 단계에는 필요한 원문과 앞 단계 JSON만 전달하며, improvement 단계에는 이미 반영된 DB/웹 원문을 다시 전달하지 않습니다.
   - 점수 범위, 0.1 단위, 비어 있지 않은 근거, 허용 level을 Pydantic에서 검증합니다.

4. Reviser
   - 배치 생성은 제거했습니다. 실측상 배치 뒤 대부분 문항을 다시 생성해 토큰이 늘었고 다른 문항의 사실이 섞였습니다.
   - 문항별로 question/original_answer만 전달하며 다른 문항과 웹 원문을 전달하지 않습니다.
   - 평가 결과에서는 여러 문항에 공통 적용할 수 있는 구조적 `improve_strategy`만 사용합니다.
   - 새 숫자, 새 영문 기술 토큰, 원문에 없는 외국 문자, 질문 전문 복사, placeholder/지나치게 짧은 결과를 코드로 검사합니다.
   - 실패 문항만 한 번 교정하며 그래도 실패하면 생성 내용을 내보내거나 전체 워크플로를 중단하지 않고 해당 원문을 보존하는 `revise_safe_fallback` 이벤트를 보냅니다.

5. 공용 실행 경로
   - Friendli 요청에 thinking, temperature, top_p, max_tokens를 명시합니다.
   - SDK 재시도는 한 번, 워크플로 노드 재시도도 한 번으로 제한합니다.
   - 실패한 노드 시도의 `AgentState` 변경은 다음 시도 전에 복원합니다.
   - 확정된 입력 오류만 재시도하지 않으며, Pydantic/생성 오류는 일반 노드 오류로 복구 대상으로 처리합니다.
   - DEBUG 로그에는 지원서 프롬프트나 생성 결과 원문을 남기지 않고 길이와 메타데이터만 남깁니다.
   - DynamoDB track-only scan에서 사용하지 않는 `#company` 표현식 이름을 보내 발생하던 ValidationException 가능성을 제거했습니다.
   - 최대 300초 LLM 대기 중 프록시 idle timeout으로 SSE가 끊기지 않도록 15초 간격 `: keep-alive` heartbeat를 보냅니다. 실제 워크플로 이벤트가 10분 동안 없으면 취소하는 기존 제한은 유지합니다.

## 2026-08-12 AWS 임베딩 데이터 전체 내보내기

- 현재 운영 설정(`ap-northeast-2`)에서 임베딩 흐름이 참조하는 데이터를 읽기 전용으로 내보냈습니다.
- DynamoDB `pertineo-document-context`: 1,991건.
- DynamoDB `pertino-resume-coordinates`: 5,046건.
- S3 Vectors `pertineo-data-vector/pertineo-data-vector-index`: 1,991건, float32 1,536차원, cosine.
- 원문 ID 1,991개와 벡터 key 1,991개가 모두 일치했고, 중복 ID/key와 양방향 누락은 없었습니다.
- 결과는 `private_exports/embedding_data_20260812/` 및 `private_exports/embedding_data_20260812.tar.gz`에 저장했습니다.
- 원문에는 개인정보가 포함될 수 있어 `private_exports/`를 `.gitignore`에 추가했습니다.
- 재실행 가능한 읽기 전용 도구는 `python/tools/export_embedding_data.py`입니다. DynamoDB는 `ConsistentRead`로 스캔하지만 DynamoDB와 S3 Vectors 전체를 묶는 원자적 스냅샷은 아닙니다.

## 2026-08-12 Upstage Embed 2 마이그레이션 준비

- 작업 브랜치는 `embedding-data-export`이며 `origin/embedding-data-export`를 추적합니다.
- Upstage 공식 계약을 확인해 최신 모델명을 `solar-embedding-2-query`와 `solar-embedding-2-passage`로 고정했습니다. 두 모델은 1,024차원이고 8K 컨텍스트를 지원합니다.
- 기존 OpenAI 인덱스는 1,536차원이므로 덮어쓰지 않습니다. 신규 대상은 `pertineo-data-vector-upstage-embed2`입니다.
- `VectorEmbedder`는 `EMBEDDING_PROVIDER`로 OpenAI/Upstage query 임베딩을 선택합니다. 실제 전환 전까지 기본값은 `openai`로 유지합니다.
- `python/tools/reembed_upstage.py`는 내보낸 원문 1,991건을 passage 모델로 배치 처리하고 신규 S3 Vector 인덱스에 적재합니다. 기존 키는 건너뛰어 재개할 수 있고, 입력 거절은 해당 ID를 실패로 기록하며 원문을 임의 절단하지 않습니다.
- 건식 실행 결과: 1,991건, 총 6,371,138자, 최대 15,157자, 20건 단위 예상 100배치. 현재 `python/.env`에는 `UPSTAGE_API_KEY`가 없어 실제 API 호출과 신규 인덱스 생성은 하지 않았습니다.
- Python 전체 테스트는 82개 통과했고 기존 Starlette/httpx deprecation warning 1개만 남았습니다.

## 2026-08-12 Upstage 전체 재임베딩 및 전환

- 사전 테스트 1건을 제외한 1,990건을 100개 배치로 추가 처리해 신규 인덱스에 총 1,991개 벡터를 적재했습니다.
- 실측 시간은 696.870초, passage 입력은 4,237,818토큰, 정가 환산 비용은 $0.08475636입니다.
- 실패·누락·추가 키는 모두 0건입니다. S3 독립 재조회에서도 1,991개 고유 키와 원문 1,991개가 완전히 일치했습니다.
- 표본 벡터는 모두 1,024차원이고 `embeddingProvider=upstage`, `embeddingModel=solar-embedding-2-passage` 메타데이터를 확인했습니다.
- canonical 샘플 A/B에서 Upstage는 0.199초, OpenAI는 0.555초였고 기업명 정확 일치는 각각 3/3, 2/3이었습니다.
- 빈도가 높은 기업·직무 20개(총 Top-3 60칸) A/B에서 Upstage/OpenAI의 기업 적중은 39/32, 직무 적중은 10/5, 동시 적중은 7/5였습니다. 이는 정답 라벨이 아닌 문자열 기반 proxy 평가입니다.
- pydantic-settings가 `.env`를 `os.environ`에 복사하지 않아 boto3가 AWS 키를 못 찾던 문제를 수정했습니다. 정적 키가 비어 있으면 기존 default provider chain을 그대로 사용합니다.
- 실제 앱 경로에서 Upstage query → 신규 S3 Top-3 → DynamoDB 원문 3건 조회가 `success`로 완료됐고 0.447초가 걸렸습니다.
- 로컬 런타임 설정을 `EMBEDDING_PROVIDER=upstage`, `S3_VECTORS_INDEX=pertineo-data-vector-upstage-embed2`로 함께 전환했습니다.
- 최종 Python 전체 테스트는 85개 통과했고 기존 deprecation warning 1개만 남았습니다.

## 2026-08-12 Upstage AWS 인덱스 삭제

- 사용자 요청으로 로컬 설정을 먼저 `EMBEDDING_PROVIDER=openai`, `S3_VECTORS_INDEX=pertineo-data-vector-index`로 롤백했습니다.
- 삭제 직전 `pertineo-data-vector-upstage-embed2`가 1,024차원/cosine/float32이고 벡터 1,991건을 포함한 것을 재확인했습니다.
- AWS S3 Vectors에서 신규 Upstage 인덱스를 삭제했습니다. 인덱스 내부 벡터 1,991건과 메타데이터도 함께 영구 삭제됐습니다.
- 기존 OpenAI `pertineo-data-vector-index`는 남아 있고 1,536차원임을 삭제 후 다시 확인했습니다.
- 로컬 원문 export, 재임베딩 도구, 실행/A-B 보고서는 보존했으므로 새 인덱스가 필요하면 비용과 시간을 들여 다시 생성할 수 있습니다.

## 2026-08-12 Upstage 벡터 로컬 재생성

- 사용자 요청에 따라 AWS 클라이언트를 생성하거나 AWS에 업로드하지 않는 `--local-output` 실행 경로를 추가했습니다.
- `document_context.jsonl.gz`의 원문 1,991건을 `solar-embedding-2-passage`로 다시 임베딩해 `private_exports/embedding_data_20260812/upstage_vectors.jsonl`에 저장했습니다.
- 각 JSONL 레코드는 기존 key/metadata와 새 1,024차원 float32 벡터, `embeddingProvider=upstage`, `embeddingModel=solar-embedding-2-passage`를 포함합니다.
- 실측 결과: 1,991/1,991건 성공, 실패·누락 0건, 4,240,142 입력 토큰, 694.794초, 정가 환산 $0.08480284입니다.
- 파일 크기는 43,865,267바이트이고 SHA-256은 `35d312afeecd82347105b3c1b19bdbb7c32384a4929bef77fd28741c0661392f`입니다.
- 별도 검증에서 JSONL 1,991줄, 고유 key 1,991개, 모든 벡터 1,024차원을 확인했습니다. 실행 보고서는 같은 폴더의 `upstage_vectors.report.json`입니다.
- 로컬 재생성 실행의 보고값은 `aws_accessed=false`이며 AWS 리소스 생성·조회·수정·업로드를 하지 않았습니다.

## 2026-08-12 OpenAI/Upstage 로컬 검색 A/B

- `python/tools/compare_local_embeddings.py`를 추가해 기존 OpenAI 1,536차원 벡터와 새 Upstage 1,024차원 벡터를 AWS 없이 정확 코사인 Top-3로 비교했습니다.
- 동일한 표준 샘플 1개와 기존 방식의 상위 기업·직무 20개를 사용했고, 20개 중 `미입력/미입력`을 제외한 19개를 주 품질 지표로 사용했습니다.
- 유효 19개에서 기업 적중은 32/57→40/57, 직무 적중은 8/57→16/57, 기업+직무 동시 적중은 6/57→10/57로 Upstage가 개선됐습니다.
- 기업 Hit@3는 13/19→17/19로 증가했으나 기업+직무 Hit@3는 양쪽 모두 4/19였습니다. Upstage는 새로운 동시 적중 쿼리를 늘리기보다 이미 찾던 쿼리 안에서 관련 문서 수와 순위를 개선했습니다.
- 기업+직무 nDCG@3는 0.412→0.659였지만 정확 문자열 기반 pair label이 존재하는 유효 쿼리는 5개뿐이어서 확정적 품질 근거로 사용할 수 없습니다.
- 기업 적중의 쿼리별 승패는 Upstage 10, 동률 6, OpenAI 3이었고 동률 제외 부호검정은 약 p=0.092로 5% 유의수준을 충족하지 않습니다.
- 21개 쿼리 API 3회 실측 중앙값은 OpenAI 0.920초, Upstage 0.156초였습니다. 초기 연결 제외 평균은 0.872초와 0.139초였습니다.
- Top-3 공통 문서는 13/60(21.7%)이므로 전환 시 EXAONE 평가에 전달되는 참고 문맥이 크게 달라질 수 있습니다.
- 상세 결과는 `private_exports/embedding_data_20260812/embedding_comparison.md`와 `embedding_comparison_report.json`에 있습니다. 전체 Python 테스트는 91개 통과했습니다.

## 2026-08-12 로컬 Upstage 벡터 전용 AWS 업로드 준비

- `python/tools/upload_local_vectors.py`를 추가했습니다. 이 도구는 `upstage_vectors.jsonl`만 읽으며 Upstage/OpenAI 임베딩 API와 DynamoDB에는 접근하지 않습니다.
- 건식 실행에서 1,991건, 1,024차원, SHA-256 `35d312afeecd82347105b3c1b19bdbb7c32384a4929bef77fd28741c0661392f`를 재검증했고 AWS 접근은 없었습니다.
- 실제 실행 시 기존 S3 Vector key를 먼저 조회해 없는 key만 최대 100건씩 업로드하므로 중단 후 재개할 수 있습니다.
- `--profile`은 dotenv의 정적 AWS key보다 우선하며, `--create-resources`를 명시한 경우에만 누락된 vector bucket/index를 생성합니다. 삭제 동작은 없습니다.
- `document_context.jsonl.gz`와 `resume_coordinates.jsonl.gz`는 읽거나 전송하지 않습니다.
- `.env.example`의 Upstage 인덱스명 오타를 수정하고 AWS session token/profile placeholder를 추가했으며 `.DS_Store`를 ignore 처리했습니다.
- 전체 Python 테스트는 94개 통과했고 변경 파일 비밀값 패턴 검사는 결과가 없었습니다.

## 2026-08-13 EXAONE 출력 신뢰성 단계별 비교 — 1차

- 사용자는 `python/scripts/analysis_result.json`의 출력량을 목표로 지정했습니다. 저장소에는 `analysis_report.json`은 없으며, PDF 생성의 입력인 이 JSON을 기준으로 삼았습니다.
- 기준 파일의 평가 텍스트는 3,827자, 수정 답변을 포함하면 5,360자입니다. `best_reply`는 문항당 258~274자입니다. 기준 파일에도 잘린 `job_summary`, 외국 문자 혼입 등이 있어 내용 결함은 복제하지 않고 분량 기준으로만 사용합니다.
- 첫 변경은 `python/resources/prompts/evaluate/system.txt`의 “답변 권장 분량 500~1000자”가 모델 출력이 아니라 입력 자기소개서 문항의 평가 기준임을 명시한 한 줄입니다. 출력 토큰 한도나 Reviser 답변 길이는 줄이지 않았습니다.
- 같은 `sample_analyze_request.json`과 고정 컨텍스트를 사용한 EXAONE 비교에서 원문 프롬프트 2회 평가 텍스트는 2,210자(전략 검증 실패)와 4,464자였고, 명확화 프롬프트 2회는 3,924자와 4,112자였으며 네 단계가 모두 성공했습니다.
- 변경안 평균 4,018자는 목표 3,827자보다 약 5% 길어 원하는 정보 밀도와 가깝습니다. 표본이 각 2회뿐이므로 실패율 개선을 확정하지 않고 임시 유지 판정했습니다.
- 사실성은 해결되지 않았습니다. 변경 결과에도 입력에 없는 결제 시스템 팀/근무 기간/특허·논문 판단과 외국 문자 혼입이 관찰됐습니다. 다음 변경 후보는 가장 먼저 생성되는 axes 단계에 “입력에서 직접 확인되는 사실만 근거로 사용하고, 누락 정보는 추정하지 말고 확인 불가로 표현”하는 단일 규칙을 추가하는 것입니다.
- Python 전체 테스트는 94개 통과했습니다. GPT 기준 비교는 `OPENAI_API_KEY`가 없어 실행하지 못했으며, 과거 실제 기본 모델은 full GPT-5.4가 아니라 `gpt-5.4-mini`였으므로 키가 준비되면 이를 주 비교군으로 사용합니다.

## 2026-08-13 EXAONE 출력 신뢰성 단계별 비교 — 2차

- 승인받은 두 번째 변경으로 axes 프롬프트에 지원자 사실의 출처를 `applicant_info`와 `questions/answers`로 한정했습니다. 누락된 팀·기간·역할·경력·성과·기술·리더십을 추정하지 않고, 부재 단정 대신 “입력에서 확인되지 않습니다”를 쓰도록 명시했습니다. 참고 컨텍스트를 지원자 경험으로 귀속하지 않는 규칙도 추가했습니다.
- 동일 `sample_analyze_request.json`, 고정된 빈 DB/웹/벡터 컨텍스트, 실제 EXAONE으로 10회 반복했습니다. axes가 생성된 9회에서 점수는 모두 x=4.3, y=4.0, z=4.1로 표준편차와 범위가 0이었습니다.
- 네 단계 전체 성공은 8/10이었습니다. 1회는 axes, 1회는 fit에서 각각 completion 4,096토큰을 모두 사용해 `LengthFinishReasonError`가 발생했습니다. 이는 정상 응답 분량 부족이 아니라 비정상 장문/반복 생성입니다.
- 완전 성공 8회의 평가 텍스트는 평균 3,908자(2,555~4,659자)로 기준 3,827자에 가깝습니다.
- 명시적 외국 문자/대체 문자는 2/10회에서 발견됐습니다: Devanagari `ध`, replacement character `�`. 또한 `involved`, `secrecy`, `K00ms`, `Kw`, `확장ing`처럼 문맥에 맞지 않는 영문 파편은 7/10회에서 발견됐습니다.
- 같은 x/y/z인데 `level`은 완전 성공 8회 중 `보통` 7회, `높음` 1회로 불일치했습니다. 축 점수 자체는 안정됐지만 level은 아직 비결정적입니다.
- “보조적 역할” 단정은 2회에서 axes에 생성되어 뒤 단계로 전파됐고, “협업이나 리더십 언급이 없어/부재” 같은 금지 표현도 후속 improvement 단계에서 반복됐습니다. axes 규칙만으로 하위 단계의 사실성 위반을 완전히 막지 못했습니다.
- 다음 단일 변경 후보는 모든 Evaluate 하위 결과에 문자·금지 단정 검증을 적용하고, 문제가 있는 하위 단계만 한 번 재실행하는 로컬 복구입니다. 사용자가 승인하기 전에는 적용하지 않습니다.

## 2026-08-13 EXAONE 재시도 오류 진단 로깅 및 성공 결과 보존

- 1·2차 프롬프트 변경만 적용된 상태에서 `sample_analyze_request.json`을 전체 워크플로로 실행해 성공 결과를 루트 `result.json`에 보존했습니다. 입력 SHA-256은 `9331fa84d688cfa4af30fe913509d5390d7874ee6b9ec862ade913dc09d7eaa7`, 결과 SHA-256은 `bf3c8371351c91f31ca8ddcd7fd5b5d9b10963d911c7b7b71a913b00ad12a146`입니다.
- 성공 결과는 `failed=false`, x=4.3/y=4.1/z=3.9, level=`높음`, 수정 답변 3건입니다. 평가+수정 텍스트는 5,510자로 목표 5,360자와 가깝습니다. 그러나 성공 처리된 내용에도 입력에 없는 `C/C++`, `Python`, `2023년 8월`, 예시 경험과 수정 답변의 replacement character `�`가 존재합니다. 따라서 이 파일은 현재 성공 판정의 실상 확인용이지 품질 승인본이 아닙니다.
- `parse_structured`가 실패 시 raw Friendli 응답을 보존해 모델/응답 스키마/오류 유형/finish reason/max tokens/프롬프트 해시/입력·캐시·출력·전체 토큰/completion ID/seed/응답 해시/괄호 균형/문장 중복률/압축률/꼬리 반복/비정상 Unicode/Pydantic 오류 위치와 안전한 입력값을 구조화 로그로 남기도록 변경했습니다. DEBUG에서만 실패 응답 앞·뒤 500자를 남깁니다.
- 워크플로 재시도 로그에는 node, 현재 시도/전체 시도, 재시도 여부, 오류 유형을 남기고, 다음 시도가 성공하면 recovery 로그를 남깁니다.
- 실제 재시도 진단에서 EVALUATE axes의 두 시도가 모두 완성된 JSON을 반환했지만 `z.score=3.98`로 동일하게 실패했습니다. 두 응답은 1,077자, 413 completion tokens, content SHA-256 prefix `b064b2351a21fbdc`로 완전히 같았습니다. temperature=0, 같은 프롬프트, 캐시된 입력을 오류 피드백 없이 재전송하므로 같은 결과가 결정적으로 반복됐습니다.
- 직접 원인은 Z축 가중합 공식이 소수 둘째 자리 값을 만들 수 있는 반면 최종 출력은 0.1 단위를 요구하는 프롬프트 충돌입니다. 현재 `AxisEvaluationReport` JSON Schema는 score를 단순 `number`로만 노출하고 Python validator의 0.1 규칙은 모델 생성 후에만 적용됩니다.
- Friendli 공식 문서상 `number`에는 minimum/maximum이 지원되지 않고 `multipleOf`도 지원 목록에 없습니다. 반면 숫자 `enum`은 지원하므로 다음 수정에서는 score를 1.0~5.0의 0.1 단위 숫자 enum으로 제한하는 방안을 우선 검토합니다.
- 4,096토큰 길이 초과는 open-ended string/array 스키마 안에서 EXAONE이 스키마상 유효한 반복 또는 공백을 계속 생성해 JSON을 닫지 못하는 별도 문제입니다. Friendli도 structured output이 유효한 토큰만 제한할 뿐 모델의 반복 선택은 막지 못하며, 명시적인 prompt/example이 필요하다고 설명합니다. 현재 axes 프롬프트가 약 9,823 tokens로 길고 일반+engineering 평가표의 규칙이 겹쳐 인지 부하가 큽니다.
- 전체 Python 테스트는 97개 통과했습니다. 점수 enum, prompt 축약, 하위 단계 국소 재실행은 아직 적용하지 않았습니다.

## 2026-08-13 EXAONE 점수 enum 적용

- `AxisEvaluation.score`를 1.0~5.0 사이의 0.1 단위 41개 숫자 enum으로 변경했습니다. 애플리케이션과 JSON 응답에서는 기존처럼 일반 `float`로 유지됩니다.
- Python `Enum` 클래스 방식은 Pydantic이 `#/$defs/AxisScore` 참조를 만들었고 Friendli가 이를 찾지 못해 생성 전 HTTP 422를 반환했습니다. 이 구현은 폐기하고, score 필드에 숫자 enum을 직접 펼치는 `Literal` 방식으로 교체했습니다.
- 동일 `sample_analyze_request.json`의 실제 EXAONE 3회에서 점수는 모두 x=4.3/y=4.2/z=4.1이었고 표준편차와 범위는 0이었습니다. 따라서 이전의 z=3.98 같은 값은 모델 디코딩 단계에서 선택할 수 없습니다.
- 3회 중 네 EVALUATE 단계 전체 성공은 2회였습니다. 나머지 1회는 점수와 무관하게 strategy의 금지된 예시 표현 검증에서 실패했습니다. 전체 성공 2회의 평가 텍스트는 3,620자와 3,719자로 기준 3,827자보다 각각 5.4%, 2.8% 짧았습니다.
- 잔여 문제는 그대로 관찰됐습니다. 1/3회에서 improvement에 아랍 문자가 섞였고, 입력에 없는 경험 부재 단정이 계속 생성됐습니다. 이 단계에서는 토큰 한도, 프롬프트 분량, 재시도, level 계산, 문자 검증을 변경하지 않았습니다.
- 평가 관련 테스트 9개와 전체 Python 테스트 98개가 통과했습니다. 다음 수정은 사용자 승인 후 별도 단계로 진행합니다.

## 2026-08-13 점수 enum 적용 후 10회 실패율

- 동일 `sample_analyze_request.json`과 고정 컨텍스트로 실제 EXAONE EVALUATE를 새로 10회 실행했습니다. 전체 단계 성공은 9/10, 실패는 1/10으로 기술적 fail률은 10%입니다.
- 실패는 strategy 1회뿐이었고 두 action-item 목록에서 금지한 예시 표현이 생성되어 Pydantic 검증에 걸렸습니다. axes/fit/improvement 실패, 길이 초과, 점수 검증 실패는 모두 0회였습니다.
- 점수는 10회 모두 x=4.3/y=4.2/z=4.1로 완전히 동일했고 각 축의 표준편차와 범위가 0이었습니다. level도 모두 `높음`이었습니다.
- 전체 EVALUATE 평균 시간은 12.870초(중앙값 12.281초, 12.076~15.613초)였습니다. 노드 평균은 axes 4.295초, fit 1.528초, improvement 5.403초, strategy 1.645초입니다.
- 성공한 9회 결과는 정규화 JSON 해시까지 모두 동일했고 평가 텍스트는 3,608자였습니다. 기준 3,827자보다 약 5.7% 짧습니다.
- 품질 관점은 별개입니다. 9/10회에서 improvement의 같은 위치에 아랍 문자 3개가 반복됐고 10/10회에서 입력 근거가 부족한 단정 진단이 발생했습니다. 따라서 현재 코드가 판정하는 기술적 성공률은 90%지만, 문자·근거 진단까지 엄격히 적용한 품질 통과율은 0/10입니다.
- 이전 10회 결과의 기술적 fail률 20%보다 이번 측정값은 10%로 낮지만, 표본이 작아 개선을 확정할 수 없습니다. 1/10 실패의 Wilson 95% 구간도 약 1.8%~40.4%로 넓습니다.
- 10회 중 성공한 9개 결과가 동일하므로 첫 성공 응답을 대표로 사용해 `python/scripts/exaone_enum_10run_evaluation_report.pdf`를 생성했습니다. 4페이지이며 모델 본문은 정제하지 않고 그대로 수록했습니다. 첫 페이지에는 9/10 성공률, 평균 12.870초, 고정 컨텍스트 EVALUATE만 실행했다는 범위, Schemer/Reviser 미실행, 문자·근거 품질 경고를 표시했습니다. 첫 페이지 렌더링을 확인한 뒤 macOS 기본 PDF 뷰어로 열었습니다.

## 2026-08-13 Schemer/Reviser 포함 전체 실행

- 앞선 10회는 점수 enum 효과만 분리하기 위해 EVALUATE 네 단계만 고정 컨텍스트로 실행했습니다. Schemer, 실시간 검색/데이터/벡터, Reviser까지 넣으면 외부 지연과 컨텍스트 변동 및 후처리 실패가 섞이므로 12.870초는 전체 파이프라인 시간이 아닙니다.
- 동일 `sample_analyze_request.json`으로 실제 전체 워크플로를 실행해 `python/scripts/exaone_full_pipeline_result.json`과 6페이지 `python/scripts/exaone_full_pipeline_report.pdf`를 만들고 PDF를 열었습니다.
- 전체 실행은 68.635초에 최종 성공했습니다. 이벤트 기준 구간은 Schemer 0.631초, WebSearch 1.920초, Data 1.288초, Evaluate 54.742초, Reviser 7.703초입니다.
- Schemer는 질문·답변 모두 재확인 없이 통과했고 사유 `정상`, 트랙 `engineering`을 반환했습니다.
- Evaluate 첫 시도 Fit이 completion 4,096토큰과 문장 중복률 99.19%의 반복 출력으로 실패했으나 전체 Evaluate 1회 재시도로 복구했습니다. 최종 점수는 x=4.3/y=4.1/z=3.9, level `높음`입니다.
- 벡터 컨텍스트는 status `failure`, 선택 키/문서 0개였습니다. 현재 런타임이 OpenAI 임베딩을 가리키지만 OpenAI 키가 없어서이며 비차단 처리되었습니다. 웹 검색과 DynamoDB 합격자 점수는 사용됐습니다.
- Reviser는 세 문항 모두 최종 결과를 반환했습니다. 2번 문항 첫 생성에 태국 문자가 섞여 문항 단위 재생성 1회로 제거됐고 안전 원문 fallback은 없었습니다. 그러나 최종 1·2번 답변에 `설계. 대용량`, `개선을 통해. 이를 통해`처럼 문장이 부자연스럽게 끊긴 부분이 남아 현재 검증이 문법 완결성을 보장하지 못함을 확인했습니다.
- 최종 Reviser에는 비정상 외국 문자가 없지만 EVALUATE `skill_fit`에는 태국 문자 U+0E32/U+0E23과 입력 근거가 약한 C/C++/Python/Redis가 남았습니다. 전체 Python 테스트는 98개 통과했습니다.

## 2026-08-13 Reviser 기존 강점 보존 + 제약 강화

- 기존 Reviser의 장점이던 상위권 지원자 수준의 전면 재구성, 직무 연결, 구체적 행동·성과 강조, 평가 피드백 활용을 한국어 프롬프트에 다시 명시했습니다. 과거 프롬프트의 원문에 없는 수치·성과·프로젝트를 의무적으로 발명하는 지시는 복원하지 않았습니다.
- 각 문항은 원문의 결론·상황·행동·선택 이유·성과·배움·직무 연결을 가능한 범위에서 재배치합니다. 평가 결과에서는 전략 이름만 편집 관점으로 전달하고, 상세 action item이나 웹 문맥을 지원자 경험으로 복사하지 않습니다.
- 본문 검증은 원문 숫자와 영문 기술의 보존, 새 숫자·기술·외국 문자 차단, 원문에 없는 구축·구현·운영·도입·배포 등의 사실 강도 상승 차단, 미래 계획의 확정 약속화 차단, 90%~175% 분량, 완결된 존댓말 문장, 중복 문장 금지를 포함합니다.
- `reply_reason`/`expectation`의 깨진 문자나 내부 필드명 때문에 유효한 본문 전체가 버려지던 문제를 분리했습니다. 본문이 통과하면 설명 필드만 검증하고, 실패한 설명만 안전한 한국어 문장으로 대체하면서 `revise_explanation_fallback` 이벤트를 남깁니다.
- 원문의 `약 85%`, `초당 5,000건`처럼 숫자의 강도·범위를 결정하는 접두 표현을 검사합니다. 모델이 접두 표현만 누락한 경우 원문에 실제 존재하는 표현만 결정적으로 복원한 뒤 전체 본문 검증을 다시 수행하고 `revise_numeric_qualifier_restore` 이벤트를 남깁니다. 숫자 접미 한정어나 다른 사실은 자동 생성하지 않습니다.
- 재시도에는 직전 `best_reply`와 본문 오류만 전달합니다. 깨진 `reply_reason`/`expectation`을 다시 문맥에 넣지 않아 EXAONE의 오류 전파와 토큰 낭비를 줄였습니다.
- 과도한 초안은 실제 EXAONE 3회에서 9/9문항이 원문 fallback되어 폐기했습니다. 숫자 한정 표현을 전역 프롬프트에 추가한 안도 fallback이 4/9로 증가해 폐기하고, 오류 시 국소 피드백과 결정적 복원 방식만 남겼습니다.
- 최종 코드로 동일 저장 입력을 실제 EXAONE에 3회 실행한 결과 모두 성공했습니다. 실행 시간은 10.481초, 10.051초, 8.295초(평균 9.609초)였고, 본문 재시도 0건, 원문 fallback 0건, 숫자 한정어 복원 3건, 설명 필드 fallback 이벤트 9건이었습니다.
- 세 실행의 `best_reply` 세트는 해시까지 완전히 동일했고 길이는 매회 272/258/212자였습니다. 최종 9/9문항은 코드 검증을 통과했고 비정상 외국 문자는 0건이었습니다. 원문의 `초당 5,000건 이상`, `800ms까지`, `120ms`, `약 85%`, `첫 2년`, `이후 3년`, Kafka/APM/N+1/MLOps 등도 보존됐습니다.
- 직접 GPT-5.4 비교는 `OPENAI_API_KEY`가 없어 실행하지 못했습니다. 저장된 이전 `analysis_result.json`과 정성 비교하면 현재 결과는 문장 확장 폭은 작지만, 이전 결과의 원문 밖 `운영`, `반응성 개선`, `평가 방식·기술 중심 문화` 추정을 최종 본문 또는 설명에서 차단합니다. 저장소의 과거 기본 모델은 full GPT-5.4가 아니라 `gpt-5.4-mini`였으므로 이를 GPT 기준선으로 명확히 구분합니다.
- 최종 검증은 Reviser/엔진 집중 테스트 40개와 Python 전체 테스트 123개가 통과했습니다. 기존 Starlette/httpx deprecation warning 1개만 남았습니다.

## 2026-08-13 Reviser 전략 적용·실제 수정 판정·7회 교정 비교

- 기존 저장 결과는 세 문항의 `best_reply`가 원문과 모두 완전히 같았습니다. 직접 원인은 Evaluate 전략에서 이름만 전달하고 action item은 버리던 구조, 생성 후보가 원문과 같아도 성공으로 인정하던 검증, 두 번 실패 시 안전 원문 fallback으로 종료하던 경로였습니다.
- Evaluate의 전략명/action item을 결론 우선·인과 연결·문장 순서 재구성·수치/성과 배치·직무 연결 같은 원문 안전 `editing_plan`으로 변환해 문항별로 전달합니다. raw action item은 KPI·새 알고리즘·운영 경험이 지원자 사실로 복사되는 위험 때문에 전달하지 않습니다.
- 생성 후보가 공백 정규화 후 원문과 같으면 실패 처리합니다. 원문이 100자 이상이면 `SequenceMatcher` 유사도 0.92 초과도 근접 복사로 보고 해당 문항만 다시 생성합니다. 재시도 판단은 LLM이 아니라 Python 검증기가 하며, 직전 후보와 `problems_to_fix`를 다음 호출에 전달합니다.
- 첫 생성은 안정적인 non-reasoning `temperature=0`, 교정 호출은 LG 권장 non-reasoning 샘플링인 `temperature=1.0`, `top_p=0.95`를 사용합니다. visible answer는 기존 글자 수 검증을 유지하고 호출당 최대 4,096토큰입니다.
- 5회·7회 실측 비교 후 사용자가 운영 기본값을 문항별 최대 5회로 확정했습니다. 동일 주어의 `사내 스터디 그룹을 조직`을 `운영`으로 표현한 경우에만 제한적으로 근거 있는 표현 변경으로 허용하며, 일반 신규 운영 주장은 계속 차단합니다.
- 최대 5회 하이브리드 실측은 5/5 기술 성공, 실제 수정 13/15(86.7%), 원문 fallback 2건, 교정 호출 32건, 평균 24.886초였습니다.
- 최대 7회 실측은 7/7 기술 성공, 실제 수정 19/21(90.5%), 원문 fallback 2건, 교정 호출 45건이었습니다. latency는 평균 25.437초, 중앙값 22.450초, p95 38.755초, 최대 42.859초였고 후보 호출은 실행당 평균 9.429회였습니다.
- 7회도 동일한 `6개월간` 누락을 해결하지 못한 실행이 있었으므로 횟수 증가는 수정률을 소폭 높이는 대신 꼬리 지연을 키웁니다. 정성 검토에서는 기간 수식 대상 변경, 원문에 없는 `삼성전자 백엔드 인턴십` 귀속, `다루는`을 `주도하는`으로 강화한 사례를 포함해 최소 5/21개에서 의미 귀속 위험을 확인했습니다. 90.5%는 구조적 수정률이지 최종 제출 품질 통과율이 아닙니다.
- 최종 코드 상한은 5회이며, 7회 결과는 비교용 실측 근거로만 보존합니다. 검증을 일찍 통과하면 5회를 모두 호출하지 않고 즉시 종료합니다.
- 원시 결과는 `python/scripts/reviser_strategy_revision_7attempts_7runs.json`, 비교 보고서는 `python/scripts/reviser_strategy_revision_report.md`와 `.pdf`입니다. PDF 첫 페이지 렌더링에서 한글과 비교표 표시를 확인했습니다.
