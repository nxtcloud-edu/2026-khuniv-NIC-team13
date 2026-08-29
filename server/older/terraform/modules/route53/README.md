# Route53 Module

이 모듈은 PERTINO 아키텍처를 위한 Route53 Hosted Zone, ACM 인증서, DNS 레코드를 생성합니다. CloudFront Distribution과 연결합니다.

## 기능

- Route53 Hosted Zone 생성 (선택사항, 기존 Zone 사용 가능)
- ACM 인증서 요청 (us-east-1, CloudFront용)
- DNS 검증 레코드 생성
- A Record 및 AAAA Record (CloudFront Alias)

## 사용법

```hcl
module "route53" {
  source = "../../modules/route53"

  domain_name              = "example.com"
  cloudfront_distribution_id = module.cloudfront.distribution_id
  environment              = "dev"
  
  create_hosted_zone     = true
  create_acm_certificate = true

  tags = {
    Environment = "dev"
    Project     = "pertino"
  }
}
```

## 변수

| 이름 | 설명 | 타입 | 기본값 | 필수 |
|------|------|------|--------|------|
| `domain_name` | 도메인 이름 | `string` | - | 예 |
| `cloudfront_distribution_id` | CloudFront Distribution ID | `string` | - | 예 |
| `create_hosted_zone` | 새 Hosted Zone 생성 여부 | `bool` | `true` | 아니오 |
| `existing_hosted_zone_id` | 기존 Hosted Zone ID | `string` | `""` | 아니오 |
| `create_acm_certificate` | ACM 인증서 생성 여부 | `bool` | `true` | 아니오 |
| `acm_certificate_arn` | 기존 ACM 인증서 ARN | `string` | `""` | 아니오 |
| `project_name` | 프로젝트 이름 | `string` | `"pertino"` | 아니오 |
| `environment` | 환경 이름 (dev/prod) | `string` | - | 예 |
| `tags` | 추가 태그 | `map(string)` | `{}` | 아니오 |

## 출력값

| 이름 | 설명 |
|------|------|
| `hosted_zone_id` | Route53 Hosted Zone ID |
| `hosted_zone_name_servers` | Hosted Zone Name Servers |
| `certificate_arn` | ACM 인증서 ARN |
| `fqdn` | Fully Qualified Domain Name |
| `cloudfront_alias_name` | CloudFront Distribution 도메인 이름 |

## 예시

### 기본 사용

```hcl
module "route53" {
  source = "../../modules/route53"

  domain_name              = "example.com"
  cloudfront_distribution_id = module.cloudfront.distribution_id
  environment              = "dev"
}
```

### 기존 Hosted Zone 사용

```hcl
module "route53" {
  source = "../../modules/route53"

  domain_name              = "example.com"
  cloudfront_distribution_id = module.cloudfront.distribution_id
  environment              = "prod"
  
  create_hosted_zone     = false
  existing_hosted_zone_id = "Z1234567890ABC"
}
```

### 기존 ACM 인증서 사용

```hcl
module "route53" {
  source = "../../modules/route53"

  domain_name              = "example.com"
  cloudfront_distribution_id = module.cloudfront.distribution_id
  environment              = "prod"
  
  create_acm_certificate = false
  acm_certificate_arn    = "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012"
}
```

## ACM 인증서

- CloudFront용 ACM 인증서는 **us-east-1** 리전에서 생성되어야 합니다
- DNS 검증을 사용합니다
- 인증서 검증 레코드가 자동으로 생성됩니다

## DNS 레코드

- **A Record**: IPv4 CloudFront Alias
- **AAAA Record**: IPv6 CloudFront Alias
- 두 레코드 모두 CloudFront Distribution을 가리킵니다

## 요구사항

- Terraform >= 1.6.0
- AWS Provider >= 5.0
- CloudFront 모듈 (Distribution ID)

## 참고

- ACM 인증서는 us-east-1 리전에서 생성됩니다
- DNS 검증은 자동으로 완료됩니다
- Hosted Zone을 생성하지 않으면 기존 Zone ID를 제공해야 합니다
- 도메인 등록 기관에서 Name Servers를 업데이트해야 합니다

