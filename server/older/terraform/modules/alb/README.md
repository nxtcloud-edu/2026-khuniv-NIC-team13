# ALB Module

이 모듈은 PERTINO 아키텍처를 위한 Application Load Balancer (ALB)를 생성합니다. Internet-facing ALB로 ECS 서비스를 외부에 노출합니다.

## 기능

- Internet-facing Application Load Balancer
- Target Group (Service A)
- HTTPS 리스너 (포트 443)
- HTTP → HTTPS 리다이렉트 (포트 80)
- Path-based 라우팅 규칙
- Health Check 설정

**참고**: Service B는 ALB에 연결되지 않고 Service Discovery를 통한 내부 통신만 사용합니다.

## 사용법

```hcl
module "alb" {
  source = "../../modules/alb"

  name         = "pertino-alb"
  environment  = "dev"
  
  subnet_ids       = module.vpc.public_subnet_ids
  security_group_id = module.vpc.alb_security_group_id
  certificate_arn  = module.route53.certificate_arn
  
  service_a_target_group_config = {
    port                 = 8080
    protocol             = "HTTP"
    health_check_path     = "/health"
    health_check_port     = 8080
    health_check_protocol = "HTTP"
  }

  tags = {
    Environment = "dev"
    Project     = "pertino"
  }
}
```

## 변수

| 이름 | 설명 | 타입 | 기본값 | 필수 |
|------|------|------|--------|------|
| `name` | ALB 이름 | `string` | `"pertino-alb"` | 아니오 |
| `subnet_ids` | Public Subnet ID 리스트 | `list(string)` | - | 예 |
| `security_group_id` | ALB Security Group ID | `string` | - | 예 |
| `certificate_arn` | ACM 인증서 ARN | `string` | `""` | 아니오 |
| `service_a_target_group_config` | Service A Target Group 설정 | `object` | - | 예 |
| `enable_http_redirect` | HTTP → HTTPS 리다이렉트 활성화 | `bool` | `true` | 아니오 |
| `idle_timeout` | 연결 유휴 타임아웃 (초) | `number` | `60` | 아니오 |
| `enable_deletion_protection` | 삭제 보호 활성화 | `bool` | `false` | 아니오 |
| `project_name` | 프로젝트 이름 | `string` | `"pertino"` | 아니오 |
| `environment` | 환경 이름 (dev/prod) | `string` | - | 예 |
| `tags` | 추가 태그 | `map(string)` | `{}` | 아니오 |

### Target Group Config 객체 구조

```hcl
{
  port                 = number  # 타겟 포트
  protocol             = string  # 프로토콜 (HTTP, HTTPS)
  health_check_path     = string  # Health Check 경로
  health_check_port     = number  # Health Check 포트
  health_check_protocol = string  # Health Check 프로토콜
}
```

## 출력값

| 이름 | 설명 |
|------|------|
| `alb_id` | ALB ID |
| `alb_arn` | ALB ARN |
| `alb_dns_name` | ALB DNS 이름 |
| `alb_zone_id` | ALB Zone ID |
| `service_a_target_group_arn` | Service A Target Group ARN |
| `service_a_target_group_id` | Service A Target Group ID |

## 예시

### 기본 사용

```hcl
module "alb" {
  source = "../../modules/alb"

  environment        = "dev"
  subnet_ids        = module.vpc.public_subnet_ids
  security_group_id = module.vpc.alb_security_group_id
  certificate_arn   = module.route53.certificate_arn
}
```

### 커스텀 Health Check

```hcl
module "alb" {
  source = "../../modules/alb"

  environment        = "prod"
  subnet_ids        = module.vpc.public_subnet_ids
  security_group_id = module.vpc.alb_security_group_id
  certificate_arn   = module.route53.certificate_arn
  
  service_a_target_group_config = {
    port                 = 8080
    protocol             = "HTTP"
    health_check_path     = "/actuator/health"
    health_check_port     = 8080
    health_check_protocol = "HTTP"
  }
  
  enable_deletion_protection = true
  idle_timeout              = 120
}
```

## 라우팅 규칙

ALB는 다음 경로 기반 라우팅을 지원합니다:

- **Service A**: `/api/service-a/*` → Service A Target Group
- **Default**: Service A Target Group로 전달

**참고**: Service B는 ALB에 연결되지 않고 Service Discovery를 통한 내부 통신만 사용합니다.

## Health Check

각 Target Group은 다음 Health Check 설정을 사용합니다:

- **Healthy Threshold**: 2
- **Unhealthy Threshold**: 2
- **Timeout**: 5초
- **Interval**: 30초
- **Success Code**: 200

## 요구사항

- Terraform >= 1.6.0
- AWS Provider >= 5.0
- VPC 모듈 (Public Subnets, ALB Security Group)
- Route53 모듈 (ACM 인증서, 선택사항)

## 참고

- ALB는 최소 2개의 서브넷이 필요합니다 (다른 AZ)
- HTTPS 리스너는 ACM 인증서가 필요합니다
- HTTP → HTTPS 리다이렉트는 301 (Permanent Redirect)를 사용합니다
- Target Group은 ECS Service와 연결되어야 합니다

