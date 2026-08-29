# WAF Module

이 모듈은 PERTINO 아키텍처를 위한 AWS WAF (Web Application Firewall) Web ACL을 생성합니다. CloudFront Distribution을 보호하기 위한 WAF 규칙을 포함합니다.

## 기능

- WAFv2 Web ACL (CloudFront scope)
- AWS Managed Rules (Core Rule Set, Known Bad Inputs, Linux OS, SQL Injection)
- Rate Limiting Rule (커스텀)
- Geo-blocking Rule (선택사항)
- WAF 로깅 설정 (선택사항)

## 사용법

```hcl
module "waf" {
  source = "../../modules/waf"

  name        = "pertino-waf"
  scope       = "CLOUDFRONT"
  environment = "dev"
  
  enable_rate_limiting = true
  rate_limit          = 2000
  
  enable_geo_blocking = false
  # allowed_countries = ["US", "KR"]
  
  enable_logging      = false
  # log_destination_arn = "arn:aws:kinesis:..."

  tags = {
    Environment = "dev"
    Project     = "pertino"
  }
}
```

## 변수

| 이름 | 설명 | 타입 | 기본값 | 필수 |
|------|------|------|--------|------|
| `name` | WAF Web ACL 이름 | `string` | `"pertino-waf"` | 아니오 |
| `scope` | WAF scope (CLOUDFRONT/REGIONAL) | `string` | `"CLOUDFRONT"` | 아니오 |
| `enable_rate_limiting` | Rate Limiting 활성화 | `bool` | `true` | 아니오 |
| `rate_limit` | Rate limit (5분당 요청 수) | `number` | `2000` | 아니오 |
| `enable_geo_blocking` | Geo-blocking 활성화 | `bool` | `false` | 아니오 |
| `allowed_countries` | 허용할 국가 코드 리스트 | `list(string)` | `[]` | 아니오 |
| `enable_logging` | WAF 로깅 활성화 | `bool` | `false` | 아니오 |
| `log_destination_arn` | 로그 대상 ARN | `string` | `""` | 아니오 |
| `project_name` | 프로젝트 이름 | `string` | `"pertino"` | 아니오 |
| `environment` | 환경 이름 (dev/prod) | `string` | - | 예 |
| `tags` | 추가 태그 | `map(string)` | `{}` | 아니오 |

## 출력값

| 이름 | 설명 |
|------|------|
| `web_acl_id` | WAF Web ACL ID |
| `web_acl_arn` | WAF Web ACL ARN |
| `web_acl_capacity` | WAF Web ACL 용량 |

## 예시

### 기본 사용

```hcl
module "waf" {
  source = "../../modules/waf"

  environment = "dev"
}
```

### Rate Limiting 커스터마이징

```hcl
module "waf" {
  source = "../../modules/waf"

  environment         = "prod"
  enable_rate_limiting = true
  rate_limit          = 5000
}
```

### Geo-blocking 활성화

```hcl
module "waf" {
  source = "../../modules/waf"

  environment         = "prod"
  enable_geo_blocking = true
  allowed_countries   = ["US", "KR", "JP"]
}
```

### 로깅 활성화

```hcl
module "waf" {
  source = "../../modules/waf"

  environment        = "prod"
  enable_logging     = true
  log_destination_arn = "arn:aws:kinesis:ap-northeast-2:123456789012:stream/waf-logs"
}
```

## AWS Managed Rules

다음 AWS Managed Rules가 포함됩니다:

1. **Core Rule Set**: OWASP Top 10 보안 위협 보호
2. **Known Bad Inputs**: 알려진 악성 입력 차단
3. **Linux Operating System**: Linux 공격 패턴 차단
4. **SQL Injection**: SQL Injection 공격 차단

## Rate Limiting

- IP 기반 Rate Limiting
- 5분당 요청 수 제한
- 기본값: 2000 requests/5 minutes
- 초과 시 요청 차단

## Geo-blocking

- 국가 코드 기반 차단/허용
- ISO 3166-1 alpha-2 형식 사용
- 허용 목록에 없는 국가는 차단

## 로깅

- Kinesis Data Firehose 또는 S3 버킷에 로그 전송
- Authorization 및 Cookie 헤더는 자동으로 마스킹
- CloudWatch Metrics와 통합

## 요구사항

- Terraform >= 1.6.0
- AWS Provider >= 5.0

## 참고

- CloudFront scope는 us-east-1 리전에서만 생성 가능
- WAF Web ACL은 CloudFront Distribution에 연결됩니다
- Rate Limiting은 IP 기반으로 작동합니다
- Geo-blocking은 국가 코드를 사용합니다

