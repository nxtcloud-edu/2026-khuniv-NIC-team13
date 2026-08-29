# Java Spring Conventions Review

Date: 2026-05-19
Skill: `java-spring-conventions`
Mode: Review mode
Scope: `pertineo.agent` Spring Boot workflow, API DTOs, workflow nodes, persistence adapter, configuration, tests.

## Summary

현재 코드는 Controller가 repository를 직접 호출하지 않고, use-case 실행을 `StateGraphEngine`으로 넘기는 점은 좋다. 하지만 `java-spring-conventions` 기준으로 보면 API boundary DTO가 mutable class이고 Bean Validation이 없으며, `AgentController`의 DTO → `AgentState` 수동 매핑 누락이 실제 품질 리스크다. `StateGraphEngine`은 service/use-case Module 역할을 하지만 routing, retry, tracing, SSE error handling을 한곳에 섞어 module interface가 얕다. 각 Node는 LLM 호출, prompt loading, state mutation, SSE serialization을 함께 처리해 test surface가 커지고 AI-readability가 낮아진다. Persistence는 controller와 분리되어 있으나 DynamoDB scan 기반 query가 데이터 증가에 취약하다. 테스트는 repository 한 케이스 외 대부분 비어 있고 `contextLoads`가 현재 실패한다.

## Findings

### Critical

없음.

### Major

- [`AgentController.startAnalysisAndSubscribe`](../src/main/java/pertineo/agent/controller/AgentController.java) Request DTO → `AgentState` 수동 매핑 누락
  - Why it matters: `AnalyzeRequestDto`에는 `backgroundCareerAward`, `linguisticAbility`, `jobField`, `division`, `applyUrl`이 있지만 controller는 일부만 `AgentState`에 복사한다. Controller는 HTTP boundary여야 하는데 field-by-field mapping knowledge까지 가진다. WebSearch/Evaluate 입력 품질이 떨어질 수 있고, 필드 추가 시 누락이 반복된다.
  - Suggested fix: `AnalyzeRequestDto`를 `record`로 전환하고 Bean Validation을 붙인 뒤, `toInitialState()` 또는 별도 mapper/command Module에서 모든 필드를 한 번에 변환한다. 변환 테스트를 추가한다.

- [`AnalyzeRequestDto`](../src/main/java/pertineo/agent/controller/dto/AnalyzeRequestDto.java) API request validation 없음
  - Why it matters: `questionList`, `answerList`, `company`, `jobPosition`, `userId`가 workflow 필수 입력처럼 사용되지만 `@NotBlank`, `@NotEmpty`, `@Size`, nested `@Valid` 같은 validation이 없다. invalid request가 LLM prompt, web search, DB query 단계까지 흘러가며 error mode가 늦게 터진다.
  - Suggested fix: request DTO에 Bean Validation을 붙이고 controller parameter에 `@Valid`를 사용한다. validation failure는 `@ControllerAdvice`로 일관된 error response를 반환한다.

- [`StateGraphEngine.runWorkflowAsync`](../src/main/java/pertineo/agent/workflow/StateGraphEngine.java) Service/use-case Module 책임 과다
  - Why it matters: `runWorkflowAsync`가 async orchestration, node routing, retry, LangSmith tracing, SSE error response, final completion을 모두 가진다. `java-spring-conventions`의 “Service represents a clear use case”와 “module interfaces are smaller than implementations” 기준에서 shallow interface다. Node 추가나 retry 정책 변경이 engine 구현 변경으로 번진다.
  - Suggested fix: workflow definition/routing, retry policy, trace wrapper, event publishing을 분리한다. `StateGraphEngine`은 `runAnalysis(InitialAnalysisCommand)` 같은 use-case entry point만 드러내게 한다.

- [`SchemerNode`, `EvaluateNode`, `ReviserNode`, `WebSearchNode`] LLM Node가 prompt loading + external call + state mutation + SSE를 함께 처리
  - Why it matters: external integration이 clear adapter 뒤에 있지 않고 Node 구현에 직접 있다. LLM output drift, prompt resource failure, SSE serialization failure를 Node 단위에서 모두 알아야 하므로 테스트가 어렵다.
  - Suggested fix: prompted LLM caller Adapter를 만든다. Node는 `schemer.classify(input)`, `evaluator.evaluate(input)`, `reviser.revise(input)` 같은 domain/use-case method만 호출하게 한다.

- [`SchemerNode`](../src/main/java/pertineo/agent/workflow/nodes/SchemerNode.java), [`EvaluateNode`](../src/main/java/pertineo/agent/workflow/nodes/EvaluateNode.java) `track`이 raw `String` contract
  - Why it matters: `SchemerNode`는 `.content()`로 track을 받고, `EvaluateNode`는 `track.equals("business")` / `track.equals("engineering")`로 분기한다. 대소문자, 줄바꿈, 설명문이 섞이면 track-specific prompt가 누락된다. domain name과 invariant가 type으로 보호되지 않는다.
  - Suggested fix: `Track` enum + parser/normalizer + structured output을 사용한다. invalid output은 명시적 application exception으로 처리한다.

- [`AgentApplicationTests.contextLoads`](../src/test/java/pertineo/agent/AgentApplicationTests.java) 현재 test suite 실패
  - Why it matters: `./gradlew test`가 `LANGSMITH_API_KEY` placeholder unresolved로 실패한다. 기본 wiring 검증이 깨져 있어 이후 refactor 안전망이 약하다.
  - Suggested fix: test properties에 `LANGSMITH_API_KEY=dummy`를 추가하거나 `application-local.yml`의 `${LANGSMITH_API_KEY}`에 기본값을 둔다. 더 나아가 context smoke test와 workflow unit/slice tests를 분리한다.

### Minor

- [`AnalyzeRequestDto`](../src/main/java/pertineo/agent/controller/dto/AnalyzeRequestDto.java), [`AgentState`](../src/main/java/pertineo/agent/workflow/nodes/state/AgentState.java) mutable Lombok `@Data` 사용
  - Why it matters: API DTO는 record 선호다. `AgentState`는 workflow 중 mutation이 필요할 수 있으나, input DTO까지 mutable이면 boundary contract가 느슨해진다.
  - Suggested fix: API request/response DTO는 record로 바꾸고, workflow state는 필요한 mutation만 노출하거나 stage별 state/result object로 나눈다.

- [`StateGraphEngine.runWorkflowAsync`](../src/main/java/pertineo/agent/workflow/StateGraphEngine.java) retry count가 workflow 전체 공용
  - Why it matters: 앞 Node에서 retry를 소모하면 뒤 Node retry 여유가 줄어든다. Retry policy가 명시적 interface가 아니라 loop local variable에 숨는다.
  - Suggested fix: node별 retry policy를 `WorkflowStepRunner` 같은 Module로 옮긴다.

- [`WebSearchNode.checkCacheAndSendSse`](../src/main/java/pertineo/agent/workflow/nodes/WebSearchNode.java) unused local `key`, unused import 존재
  - Why it matters: AI-readability를 떨어뜨리고 실제 cache key 규칙을 혼동시킨다.
  - Suggested fix: unused code/import 제거. cache key 생성은 한 Module/메서드에서 표현한다.

- [`PreviousResumeDataTemp`](../src/main/java/pertineo/agent/repository/PreviousResumeDataTemp.java) fake Adapter behavior가 production repository와 다름
  - Why it matters: `getScoreByCompanyAndTrack`, `getScoreByTrack` 등이 production path와 다르게 empty를 반환한다. profile 전환 시 테스트/로컬 behavior가 실제와 어긋난다.
  - Suggested fix: fake Adapter도 production Interface의 주요 query behavior를 구현하거나 test-only fake로 위치/이름을 명확히 한다.

- [`AnalysisReport`](../src/main/java/pertineo/agent/data/AnalysisReport.java) current workflow result와 중복/미사용 가능성
  - Why it matters: final response shape가 `EvaluateNode.ResumeEvaluation` + `ReviserNode.RevisedAnswerInfo`와 분리되어 있어 어떤 response contract가 canonical인지 헷갈린다.
  - Suggested fix: 사용처 확인 후 삭제하거나 final response DTO로 통합한다.

### Suggestions

- [`pertineo.agent.controller`, `workflow`, `repository`, `cache`, `trace`] 현재 package가 기술 계층 중심
  - Feature/domain package 구조를 선호한다. 예: `pertineo.agent.analysis`, `pertineo.agent.analysis.workflow`, `pertineo.agent.analysis.persistence`, `pertineo.agent.analysis.web`처럼 “분석” use case 중심으로 모으면 entry point가 더 뚜렷해진다.

- [`LangSmithTracer`](../src/main/java/pertineo/agent/trace/LangSmithTracer.java) external integration Adapter 명확화
  - `LangSmithTraceClient` 또는 `WorkflowTracer` interface 뒤에 두면 tracing off/fake/test가 쉬워진다.

- [`LocalWebSearchCache`](../src/main/java/pertineo/agent/cache/LocalWebSearchCache.java) cache key semantic 명명
  - `WebSearchCacheKey.of(position, company)` 같은 작은 value object나 key method를 두면 company/position order 혼동을 줄인다.

## Positive matches

- Controller가 repository를 직접 호출하지 않는다. `AgentController`는 `StateGraphEngine`만 호출한다.
- API boundary DTO가 존재한다. `AnalyzeRequestDto`, `SseEvent`가 controller package 아래 있다.
- repository Interface와 DynamoDB Adapter가 분리되어 있다. `PreviousResumeDataRepository`와 `DynamoDbPreviousResumeDataRepository`가 있다.
- `DynamoDbPreviousResumeDataRepositoryTest`가 pagination/average behavior를 public method로 검증한다.
- secrets는 code에 hardcode하지 않고 `application-local.yml`, `application-prod.yml`에서 environment variable을 사용한다.
- `DynamoDBProperties`로 DynamoDB config를 type-safe config에 가깝게 묶었다.
- `@EnableAsync`, `@EnableCaching`처럼 async/cache concern이 application config에서 명시되어 있다.

## Tests / verification

- Existing tests checked:
  - `./gradlew test` 실행.
  - `DynamoDbPreviousResumeDataRepositoryTest` 통과.
  - `AgentApplicationTests.contextLoads()` 실패.
- Missing tests:
  - `AnalyzeRequestDto` validation tests.
  - Request DTO → `AgentState` mapping tests.
  - `SchemerNode` track normalization/invalid output tests.
  - `StateGraphEngine` node routing/retry behavior tests.
  - `WorkflowEventPublisher`/SSE event shape tests.
  - `WebSearchNode` cache hit/miss behavior tests.
  - LLM output null/format drift tests with fake ChatClient/adapter.
- Recommended targeted tests:
  - `AnalyzeRequestMapperTest`: every field maps from request to initial state.
  - `TrackParserTest`: accepts `business`, `business\n`, `Business`; rejects unknown with clear error.
  - `StateGraphEngineTest`: retries same node up to configured count and stops on validation failure.
  - `DynamoDbPreviousResumeDataRepositoryTest`: track fallback query and malformed number handling.

## Risk areas

- Business ambiguity: track classification is binary (`business`/`engineering`) and LLM-driven. Product rule for ambiguous roles is not codified.
- Transaction/data consistency: no JPA transaction issue observed. DynamoDB read path uses full scans and aggregation in application code, so latency/cost risk grows with data.
- Security/privacy: request/response includes applicant info and full final state is sent via SSE. Need confirm whether `final_state` should expose all state fields. LangSmith tracing serializes inputs/outputs; PII policy should be explicit.
- AI-readability: entry point exists but responsibilities are mixed. Side effects are not isolated: LLM calls, Tavily HTTP calls, cache writes, tracing, SSE events, and state mutation sit inside Node implementations.
