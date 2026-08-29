# Performance Improvement Opportunities

## Summary

현재 프로젝트의 주요 성능 병목 후보는 DynamoDB `scan`, 직렬 LLM/Tavily 호출, 동기 LangSmith trace 전송이다. 개선 효과는 크게 세 영역이다.

- **Latency 감소**: 요청 응답 시간, 특히 tail latency 안정화
- **Cost 감소**: DynamoDB read capacity, LLM 호출, 외부 API 낭비 축소
- **Operational stability 개선**: 동시 요청 폭주, 외부 API 지연, 큰 SSE payload에 대한 내성 강화

## Priority Map

| Priority | Target | Main effect | User-visible impact |
| --- | --- | --- | --- |
| P1 | DynamoDB `scan` 제거 | DB 읽기량/비용 감소 | 데이터 증가에도 응답 지연 덜 증가 |
| P1 | Schemer LLM 호출 병합 | LLM round-trip 1회 제거 | 요청당 수 초 단축 가능 |
| P2 | Tavily 검색 병렬화 | 웹검색 wall-clock 단축 | 검색 단계 체감 속도 개선 |
| P2 | LangSmith 비동기 전송 | trace API가 workflow를 막지 않음 | tail latency 안정 |
| P3 | Prompt/resource 캐싱 | 반복 I/O/parse 제거 | 작지만 꾸준한 overhead 감소 |
| P3 | Async executor 명시 | 동시성/backpressure 제어 | 폭주 상황에서 서버 안정 |
| P3 | SSE final payload 축소 | 네트워크/브라우저 부담 감소 | 완료 이벤트 가벼움 |

## 1. Replace DynamoDB Scan With Query / GSI

### Current code

- `src/main/java/pertineo/agent/repository/DynamoDbPreviousResumeDataRepository.java`
  - `scanAll(...)`: `ScanRequest` + `filterExpression`로 전체 테이블 스캔
  - `getScoreByCompanyAndTrack(...)`, `getScoreByTrack(...)` 등 모든 조회가 scan 기반
- `src/main/java/pertineo/agent/workflow/nodes/DataNode.java`
  - `company + track` 조회 후 fallback으로 `track` 조회

### Problem

`Scan`은 조건에 맞는 row만 필요한 상황에서도 테이블 전체를 읽는다. 데이터가 커질수록 latency와 read capacity cost가 같이 증가한다.

### Improvement

- DynamoDB table에 조회 패턴별 GSI 추가
  - `companyTrackIndex`: partition key = `company`, sort key = `track`
  - `trackIndex`: partition key = `track`
- repository에서 `ScanRequest` 대신 `QueryRequest` 사용
- 가능하면 평균 점수 pre-aggregate table 도입
  - key: `company#track`, `track`
  - value: `count`, `avgX`, `avgY`, `avgZ`, `avgOverall`

### Expected effect

- DB read complexity: `O(table size)` → `O(matched partition size)` 또는 aggregate 사용 시 `O(1)`
- 데이터 증가 시 성능 저하 완화
- DynamoDB 비용 예측 가능성 증가

## 2. Merge Schemer Validation And Track Classification

### Current code

- `src/main/java/pertineo/agent/workflow/nodes/SchemerNode.java`
  - first LLM call: question/answer validation
  - second LLM call: track classification

### Problem

한 입력에 대해 LLM을 두 번 호출한다. 네트워크 round-trip과 model latency가 중복된다.

### Improvement

`SchemerValidationResult` structured output에 `track` 필드를 포함한다.

Example target shape:

```java
private record SchemerValidationResult(
        @JsonProperty("is_question_valid") boolean isQuestionValid,
        @JsonProperty("is_answer_valid") boolean isAnswerValid,
        @JsonProperty("validation_reason") String validationReason,
        @JsonProperty("track") String track
) {}
```

### Expected effect

- 요청당 LLM 호출 1회 감소
- LLM 비용 감소
- 전체 workflow latency 즉시 감소

## 3. Parallelize Tavily Searches

### Current code

- `src/main/java/pertineo/agent/workflow/nodes/WebSearchNode.java`
  - `for (ToolPlan plan : planResponse.plans())` 안에서 `performTavilySearch(...)` 순차 호출
  - `performTavilySearch(...)` 내부에서 `RestClient.create()` 매번 생성

### Problem

검색 계획이 여러 개면 요청 시간이 합산된다.

```text
current latency ~= search1 + search2 + search3
parallel latency ~= max(search1, search2, search3)
```

### Improvement

- `RestClient`를 Spring bean 또는 node field로 재사용
- timeout 설정 추가
- bounded executor로 Tavily 호출 병렬화
- 실패한 검색은 빈 결과로 degrade하되 전체 workflow는 계속 진행

### Expected effect

- 웹검색 단계 wall-clock time 감소
- 외부 API 지연에 대한 내성 증가
- connection/client 생성 overhead 감소

## 4. Make LangSmith Trace Sending Non-Blocking

### Current code

- `src/main/java/pertineo/agent/trace/LangSmithTracer.java`
  - method name: `sendRequestAsync(...)`
  - actual behavior: `httpClient.send(...)` blocking call

### Problem

trace API 지연/장애가 workflow thread를 막을 수 있다. span start/end마다 외부 HTTP가 끼어든다.

### Improvement

- `HttpClient.sendAsync(...)` 사용
- trace 전용 bounded executor/queue 사용
- production sampling 설정 추가
- 민감정보 포함 payload 축소

### Expected effect

- tail latency 감소
- LangSmith 장애가 사용자 요청에 미치는 영향 축소
- 개인정보/비용 리스크 감소

## 5. Cache Prompt And Resource Files

### Current code

- `SchemerNode`: `promptsResource.getInputStream()` per request
- `WebSearchNode`: `promptsResource.getInputStream()` per request
- `EvaluateNode`: prompt/resource files read per request
- `ReviserNode`: prompt/resource files read per request

### Problem

작은 비용이지만 매 요청마다 file/resource read와 JSON parse가 반복된다.

### Improvement

- `@PostConstruct`에서 prompt template 로드
- immutable field로 보관
- track별 eval prompt도 미리 합성 가능

### Expected effect

- CPU/I/O overhead 감소
- node logic 단순화
- 테스트 쉬워짐

## 6. Configure Async Executor Explicitly

### Current code

- `AgentApplication.java`: `@EnableAsync`
- `StateGraphEngine.java`: `@Async`
- 별도 `TaskExecutor` 설정 없음

### Problem

기본 async executor는 운영 트래픽에서 thread/queue/backpressure 정책이 불명확하다.

### Improvement

- `ThreadPoolTaskExecutor` bean 추가
- core/max pool, queue capacity, thread name, rejection policy 설정
- workflow 단위 timeout/cancellation 정책 추가

### Expected effect

- 동시 요청 폭주 시 더 예측 가능한 동작
- 서버 thread 고갈 방지
- 장애 원인 추적 쉬움

## 7. Reduce SSE Final Payload

### Current code

- `src/main/java/pertineo/agent/workflow/nodes/ReviserNode.java`
  - `sendSse(..., "final_state", ..., state)`로 전체 `AgentState` 전송

### Problem

`AgentState`에는 질문/답변, web context, DB context, evaluation result, revised result 등이 들어갈 수 있다. 최종 이벤트 payload가 커질 수 있고, 민감정보 노출 범위도 넓다.

### Improvement

- 최종 응답 DTO 생성
- 클라이언트에 필요한 필드만 전송
- trace/SSE 모두에서 민감정보 최소화

### Expected effect

- 네트워크 payload 감소
- 브라우저 parsing 부담 감소
- 개인정보 노출 리스크 감소

## Recommended Execution Order

1. **Schemer LLM 호출 병합**
   - 코드 변경 작음
   - 효과 즉시 체감
   - 테스트 작성 쉬움

2. **DynamoDB `QueryRequest` 전환 + GSI 설계**
   - 성능/비용 효과 가장 큼
   - table/index migration 고려 필요

3. **LangSmith non-blocking 전송**
   - 운영 안정성 효과 큼
   - 사용자-facing behavior 변화 작음

4. **Tavily 병렬화 + timeout**
   - 웹검색 latency 개선
   - 외부 API 장애 처리 정책 같이 필요

5. **Prompt cache / executor / SSE payload 축소**
   - 구조 정리와 안정성 개선
   - 앞선 변경 이후 묶어서 진행 가능

## Measurement Plan

개선 전후로 아래 지표를 남긴다.

- End-to-end workflow latency
  - p50 / p95 / p99
- Node별 latency
  - SCHEMER / WEBSEARCH / DATA / EVALUATE / REVISE
- LLM call count per request
- Tavily call count and duration
- DynamoDB consumed capacity / request count
- SSE total bytes per request
- LangSmith trace send failure/latency

## Expected Overall Result

가장 큰 변화는 사용자 체감 응답 시간과 비용이다.

- 작은 데이터/낮은 트래픽: LLM 호출 병합, Tavily 병렬화가 먼저 체감됨
- 큰 데이터/운영 트래픽: DynamoDB query 전환과 async executor 설정 효과가 커짐
- 장애 상황: LangSmith 비동기화, Tavily timeout, payload 축소가 안정성에 기여함
