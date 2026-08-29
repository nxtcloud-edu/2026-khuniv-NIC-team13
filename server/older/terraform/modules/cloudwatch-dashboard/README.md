# CloudWatch Dashboard Module

이 모듈은 PERTINO 아키텍처를 위한 CloudWatch 커스텀 대시보드를 생성합니다.

## 기능

- ECS 서비스 모니터링 (CPU, Memory, Task Count, Network I/O)
- ALB 메트릭 모니터링 (Request Count, Response Time, Status Codes, Target Health)
- DynamoDB 테이블 모니터링 (Capacity, Throttling, Errors, Latency)
- CloudWatch Logs 통합 (최근 로그, 에러 로그)

## 사용법

```hcl
module "cloudwatch_dashboard" {
  source = "../../modules/cloudwatch-dashboard"

  project_name   = "pertino"
  environment    = "prod"
  dashboard_name = "Pertineo-monitor"

  # ECS Configuration
  cluster_name   = module.ecs.cluster_name
  service_a_name = "service-a"
  service_b_name = "service-b"

  # ALB Configuration
  alb_arn_suffix          = module.alb.alb_arn_suffix
  target_group_arn_suffix = module.alb.target_group_arn_suffix

  # DynamoDB Tables
  dynamodb_table_names = [
    "pertino-prod-lock",
    "pertino-prod-access-code",
    "pertino-prod-popup",
    "pertino-prod-notice",
    "pertino-prod-email",
    "pertino-prod-admin",
    "pertino-prod-properties",
    "pertino-prod-whitelist"
  ]

  # CloudWatch Logs
  service_a_log_group = "/ecs/pertino-cluster/service-a"
  service_b_log_group = "/ecs/pertino-cluster/service-b"

  tags = {
    Environment = "prod"
    Project     = "pertino"
  }
}
```

## 변수

| 이름 | 설명 | 타입 | 기본값 | 필수 |
|------|------|------|--------|------|
| `project_name` | 프로젝트 이름 | `string` | `"pertino"` | 아니오 |
| `environment` | 환경 이름 (dev/prod) | `string` | - | 예 |
| `dashboard_name` | 대시보드 이름 | `string` | `"Pertineo-monitor"` | 아니오 |
| `region` | AWS 리전 | `string` | `"ap-northeast-2"` | 아니오 |
| `cluster_name` | ECS 클러스터 이름 | `string` | - | 예 |
| `service_a_name` | Service A 이름 | `string` | `"service-a"` | 아니오 |
| `service_b_name` | Service B 이름 | `string` | `"service-b"` | 아니오 |
| `alb_arn_suffix` | ALB ARN 접미사 | `string` | - | 예 |
| `target_group_arn_suffix` | Target Group ARN 접미사 | `string` | - | 예 |
| `dynamodb_table_names` | DynamoDB 테이블 이름 목록 | `list(string)` | `[]` | 아니오 |
| `service_a_log_group` | Service A 로그 그룹 | `string` | - | 예 |
| `service_b_log_group` | Service B 로그 그룹 | `string` | - | 예 |
| `tags` | 추가 태그 | `map(string)` | `{}` | 아니오 |

## 출력값

| 이름 | 설명 |
|------|------|
| `dashboard_arn` | CloudWatch Dashboard ARN |
| `dashboard_name` | CloudWatch Dashboard 이름 |

## 대시보드 구조

### 1. ECS Overview
- Service A/B CPU 사용률
- Service A/B Memory 사용률
- Task Count (Running vs Desired)
- Network I/O

### 2. ALB Metrics
- Request Count (전체 요청 수)
- Target Response Time (평균, p95, p99)
- Active/New Connections
- HTTP Status Codes (2XX, 4XX, 5XX)
- Target Group Health
- Error Rate (%)

### 3. DynamoDB Metrics
- Read/Write Capacity Units
- Throttled Requests
- User/System Errors
- Request Latency

### 4. Application Logs
- Service A/B 최근 50개 로그
- Service A/B 에러 로그
- Error Log Count Over Time

## 참고

- Container Insights가 활성화되어 있어야 ECS 메트릭이 수집됩니다.
- DynamoDB 테이블이 PAY_PER_REQUEST 모드인 경우 Throttled Requests는 거의 발생하지 않습니다.
- 로그 위젯은 CloudWatch Logs Insights 쿼리를 사용합니다.
