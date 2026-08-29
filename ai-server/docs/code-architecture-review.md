# Code Architecture Review

Date: 2026-05-19
Scope: Spring AI workflow architecture, controller input mapping, LLM output handling, SSE/event flow, persistence query, test surface.

## Ranked synthesis

| Rank | Explanation | Confidence | Basis |
|---:|---|---|---|
| 1 | Workflow Module이 너무 많은 책임을 가짐. Node 실행, routing, retry, SSE, tracing이 섞임. | High | `StateGraphEngine.java:29-99`, 각 Node의 `sendSse` 반복 |
| 2 | 입력 DTO → `AgentState` 매핑 누락으로 평가 품질이 흔들림. | High | `AnalyzeRequestDto.java:20-31` 필드 존재, `AgentController.java` 매핑 일부 누락 |
| 3 | LLM 출력 Interface가 약함. `track`/result null/format drift에 취약. | High | `SchemerNode.java:66-82`, `EvaluateNode.java:65-68`, `ReviserNode.java:58-66` |
| 4 | DynamoDB query Module은 동작하지만 scan 기반이라 데이터 증가 시 비용/지연 위험. | Medium | `DynamoDbPreviousResumeDataRepository.java:96-124` |
| 5 | test surface 부족. `contextLoads`도 현재 실패. | High | `./gradlew test` 실패, `LANGSMITH_API_KEY` placeholder |

## Findings

### Critical

없음. 지금 보이는 것은 즉시 보안 사고나 데이터 파괴보다 안정성·구조 문제다.

### Major

#### 1. `AgentController` 입력 매핑 누락

**Evidence**

- `AnalyzeRequestDto.java:20-31`에 `backgroundCareerAward`, `linguisticAbility`, `jobField`, `division`, `applyUrl` 있음.
- `AgentState.java:26-37`에도 대응 필드 있음.
- `AgentController.java`는 일부만 `set`함.

**Why**

지원자 스펙, 직군, 부서, 공고 URL이 workflow에 전달되지 않는다. WebSearch/Evaluate 품질이 하락할 수 있다.

**Suggested fix**

request DTO → state 변환 factory/mapper Module을 만들고 매핑 테스트를 둔다.

#### 2. LLM track 분류가 raw `String` output

**Evidence**

- `SchemerNode.java:66-71`에서 `.content()` 사용.
- `EvaluateNode.java:65-68`에서 `track.equals("business")` / `track.equals("engineering")` 사용.

**Why**

`"business\n"`, `"Business"`, 설명문 포함 output이면 track resource가 붙지 않는다. DB scan도 raw track 값을 그대로 사용한다.

**Suggested fix**

`Track` enum + structured output + normalize/validate Module을 둔다.

#### 3. Workflow Module Interface가 shallow

**Evidence**

- `StateGraphEngine.java:37-87`가 node name string, retry, switch routing을 전부 관리한다.

**Why**

Node 추가나 순서 변경마다 engine을 수정해야 한다. Interface가 “노드 실행”보다 “노드 이름 문자열 규약”까지 알게 만든다.

**Suggested fix**

Workflow Definition Module로 routing table/transition을 감춘다.

#### 4. SSE 전송 코드 중복

**Evidence**

- `SchemerNode.java:102-110`
- `EvaluateNode.java:106-114`
- `ReviserNode.java:126-134`
- `DataNode`도 동일 패턴

**Why**

event format 변경이나 에러 처리 변경이 여러 Node에 퍼진다. Locality가 낮다.

**Suggested fix**

`WorkflowEventPublisher` Module을 둔다. Node는 semantic event만 발행한다.

#### 5. 테스트 현재 실패

**Evidence**

- `./gradlew test` → `AgentApplicationTests.contextLoads()` fail.
- Root evidence: `LANGSMITH_API_KEY` placeholder unresolved in `LangSmithTracer`.

**Why**

기본 test profile이 `local`이고 LangSmith env가 필요하다.

**Suggested fix**

`AgentApplicationTests` test property에 `LANGSMITH_API_KEY=dummy`를 추가하거나 config default를 yml placeholder에도 제공한다.

## Deepening opportunities

### 1. Application Intake Module

**Files**

- `AgentController`
- `AnalyzeRequestDto`
- `AgentState`

**Problem**

DTO → State 변환 knowledge가 controller에 흩어져 있고 일부 필드가 누락된다.

**Solution**

작은 Interface를 둔다. 예: `AnalysisRequest.toInitialState()` 또는 mapper.

**Benefits**

Locality가 높아진다. 누락 필드 테스트가 쉬워진다. Controller가 얇아진다.

### 2. Workflow Runtime Module

**Files**

- `StateGraphEngine`
- `AgentNode`
- all nodes

**Problem**

routing, retry, tracing, SSE가 한 loop에 섞여 있다.

**Solution**

workflow step 실행 Interface 뒤에 retry + trace + event wrapping을 둔다.

**Benefits**

Node Implementation은 business step만 가진다. Routing 변경 leverage가 커진다.

### 3. Workflow Event Publisher Module

**Files**

- all `sendSse` implementations

**Problem**

SSE serialization이 반복된다.

**Solution**

`publish(type, status, data)` Adapter를 둔다.

**Benefits**

event contract가 한 곳에 모인다. 테스트 seam이 명확해진다.

### 4. Track Classification Module

**Files**

- `SchemerNode`
- `EvaluateNode`
- `DataNode`
- repository query callers

**Problem**

track이 raw `String` Interface다.

**Solution**

`Track` enum + parser + validation을 둔다.

**Benefits**

LLM drift를 방어한다. DB query 안정성이 올라간다.

### 5. Prompted LLM Client Module

**Files**

- `SchemerNode`
- `WebSearchNode`
- `EvaluateNode`
- `ReviserNode`

**Problem**

prompt loading + `ChatClient` call + output parsing이 반복된다.

**Solution**

task-specific caller Interface 뒤에 prompt/resource/format handling을 둔다.

**Benefits**

LLM failure tests가 쉬워진다. Prompt contract locality가 올라간다.

## Tests / verification

- Command: `./gradlew test`
- Result: failed
- Passing: `DynamoDbPreviousResumeDataRepositoryTest`
- Failing: `AgentApplicationTests.contextLoads()` due unresolved `LANGSMITH_API_KEY`

## Unknowns / limits

- `CONTEXT.md`, `docs/adr`는 발견되지 않았다.
- Domain vocabulary는 code에서만 추론했다.
- Repository evidence 기준 현재 dependency는 LangChain4j가 아니라 Spring AI다.
