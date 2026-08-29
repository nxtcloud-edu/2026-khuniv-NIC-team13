# CloudFront Module

이 모듈은 PERTINO 아키텍처를 위한 CloudFront Distribution을 생성합니다. S3 Origin과 ALB Origin을 연결하고, WAF를 통한 보안을 제공합니다.

## 기능

- CloudFront Distribution 생성
- S3 Origin (OAC) - Default Behavior
- ALB Origin - Path-based Behavior (`/api/*`)
- Custom Error Responses (404, 403 → index.html)
- WAF Web ACL 연결
- Price Class 설정
- 로깅 설정 (선택사항)

## 사용법

```hcl
module "cloudfront" {
  source = "../../modules/cloudfront"

  environment = "dev"
  
  aliases = ["example.com", "www.example.com"]
  
  s3_origin_config = {
    bucket_name = module.s3.bucket_id
    oac_id      = module.s3.oac_id
  }
  
  alb_origin_config = {
    alb_dns_name = module.alb.alb_dns_name
    alb_zone_id  = module.alb.alb_zone_id
  }
  
  certificate_arn = module.route53.certificate_arn
  waf_web_acl_id  = module.waf.web_acl_id
  
  price_class = "PriceClass_100"

  tags = {
    Environment = "dev"
    Project     = "pertino"
  }
}
```

## 변수

| 이름 | 설명 | 타입 | 기본값 | 필수 |
|------|------|------|--------|------|
| `aliases` | CloudFront 별칭 (도메인) 리스트 | `list(string)` | `[]` | 아니오 |
| `s3_origin_config` | S3 Origin 설정 | `object` | - | 예 |
| `alb_origin_config` | ALB Origin 설정 | `object` | - | 예 |
| `certificate_arn` | ACM 인증서 ARN | `string` | `""` | 아니오 |
| `waf_web_acl_id` | WAF Web ACL ID | `string` | `""` | 아니오 |
| `price_class` | Price Class | `string` | `"PriceClass_100"` | 아니오 |
| `enable_logging` | CloudFront 로깅 활성화 | `bool` | `false` | 아니오 |
| `log_bucket` | 로그 저장 S3 버킷 | `string` | `""` | 아니오 |
| `log_prefix` | 로그 파일 접두사 | `string` | `""` | 아니오 |
| `project_name` | 프로젝트 이름 | `string` | `"pertino"` | 아니오 |
| `environment` | 환경 이름 (dev/prod) | `string` | - | 예 |
| `tags` | 추가 태그 | `map(string)` | `{}` | 아니오 |

### S3 Origin Config 객체 구조

```hcl
{
  bucket_name = string  # S3 버킷 이름
  oac_id      = string  # Origin Access Control ID
}
```

### ALB Origin Config 객체 구조

```hcl
{
  alb_dns_name = string  # ALB DNS 이름
  alb_zone_id  = string  # ALB Zone ID
}
```

## 출력값

| 이름 | 설명 |
|------|------|
| `distribution_id` | CloudFront Distribution ID |
| `distribution_arn` | CloudFront Distribution ARN |
| `domain_name` | CloudFront Distribution 도메인 이름 |
| `hosted_zone_id` | CloudFront Distribution Hosted Zone ID |
| `distribution_status` | CloudFront Distribution 상태 |

## 예시

### 기본 사용

```hcl
module "cloudfront" {
  source = "../../modules/cloudfront"

  environment = "dev"
  
  s3_origin_config = {
    bucket_name = module.s3.bucket_id
    oac_id      = module.s3.oac_id
  }
  
  alb_origin_config = {
    alb_dns_name = module.alb.alb_dns_name
    alb_zone_id  = module.alb.alb_zone_id
  }
}
```

### 커스텀 도메인 및 WAF

```hcl
module "cloudfront" {
  source = "../../modules/cloudfront"

  environment = "prod"
  
  aliases = ["api.example.com"]
  
  s3_origin_config = {
    bucket_name = module.s3.bucket_id
    oac_id      = module.s3.oac_id
  }
  
  alb_origin_config = {
    alb_dns_name = module.alb.alb_dns_name
    alb_zone_id  = module.alb.alb_zone_id
  }
  
  certificate_arn = module.route53.certificate_arn
  waf_web_acl_id  = module.waf.web_acl_id
  
  price_class = "PriceClass_All"
  
  enable_logging = true
  log_bucket     = "cloudfront-logs-bucket"
  log_prefix     = "cloudfront/"
}
```

## Origin 및 Behavior

### Default Behavior (S3)
- **Origin**: S3 버킷 (OAC 사용)
- **Path**: 모든 경로 (기본)
- **Caching**: 1시간 (3600초)
- **Compression**: 활성화

### Path-based Behavior (ALB)
- **Origin**: ALB
- **Path**: `/api/*`
- **Caching**: 비활성화 (0초)
- **Forward**: Query String, Headers, Cookies 모두 전달

## Custom Error Responses

- **404 (Not Found)**: `/index.html`로 리다이렉트 (SPA 지원)
- **403 (Forbidden)**: `/index.html`로 리다이렉트 (SPA 지원)

## Price Class

- **PriceClass_100**: 가장 저렴한 지역 (미국, 캐나다, 유럽)
- **PriceClass_200**: PriceClass_100 + 아시아, 중동, 아프리카
- **PriceClass_All**: 모든 지역

## 요구사항

- Terraform >= 1.6.0
- AWS Provider >= 5.0
- S3 모듈 (버킷, OAC)
- ALB 모듈 (ALB DNS, Zone ID)
- WAF 모듈 (선택사항)
- Route53 모듈 (선택사항, ACM 인증서)

## 참고

- CloudFront Distribution 생성에는 시간이 걸립니다 (15-20분)
- S3 Origin은 OAC를 사용하여 보안을 강화합니다
- ALB Origin은 HTTPS만 허용합니다
- WAF Web ACL은 CloudFront scope여야 합니다
- Custom Error Responses는 SPA (Single Page Application)를 지원합니다

