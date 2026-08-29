# S3 Module

이 모듈은 PERTINO 아키텍처를 위한 S3 버킷을 생성합니다. Frontend 정적 파일 호스팅을 위한 버킷과 CloudFront Origin Access Control (OAC)을 포함합니다.

## 기능

- S3 버킷 생성 (Frontend 호스팅용)
- 버전 관리
- Server-side Encryption
- Public Access Block
- CloudFront Origin Access Control (OAC)
- 버킷 정책 (CloudFront OAC 접근 허용)

## 사용법

```hcl
module "s3" {
  source = "../../modules/s3"

  bucket_name = "pertino-frontend-dev"
  environment = "dev"
  
  enable_versioning = true
  enable_encryption = true
  block_public_access = true

  tags = {
    Environment = "dev"
    Project     = "pertino"
  }
}
```

## 변수

| 이름 | 설명 | 타입 | 기본값 | 필수 |
|------|------|------|--------|------|
| `bucket_name` | S3 버킷 이름 | `string` | - | 예 |
| `enable_versioning` | 버전 관리 활성화 | `bool` | `true` | 아니오 |
| `enable_encryption` | Server-side Encryption 활성화 | `bool` | `true` | 아니오 |
| `kms_key_id` | KMS Key ID (선택사항, 없으면 AES256) | `string` | `null` | 아니오 |
| `block_public_access` | 모든 Public Access 차단 | `bool` | `true` | 아니오 |
| `project_name` | 프로젝트 이름 | `string` | `"pertino"` | 아니오 |
| `environment` | 환경 이름 (dev/prod) | `string` | - | 예 |
| `tags` | 추가 태그 | `map(string)` | `{}` | 아니오 |

## 출력값

| 이름 | 설명 |
|------|------|
| `bucket_id` | S3 버킷 ID |
| `bucket_arn` | S3 버킷 ARN |
| `bucket_domain_name` | 버킷 도메인 이름 |
| `bucket_regional_domain_name` | 리전별 버킷 도메인 이름 |
| `oac_id` | CloudFront OAC ID |
| `oac_arn` | CloudFront OAC ARN |

## 예시

### 기본 사용

```hcl
module "s3" {
  source = "../../modules/s3"

  bucket_name = "pertino-frontend-dev"
  environment = "dev"
}
```

### KMS 암호화 사용

```hcl
module "s3" {
  source = "../../modules/s3"

  bucket_name = "pertino-frontend-prod"
  environment  = "prod"
  
  enable_encryption = true
  kms_key_id       = "arn:aws:kms:ap-northeast-2:123456789012:key/12345678-1234-1234-1234-123456789012"
}
```

## CloudFront Origin Access Control (OAC)

이 모듈은 자동으로 CloudFront OAC를 생성하고 버킷 정책을 설정합니다:

- OAC를 통해서만 버킷에 접근 가능
- Public Access는 완전히 차단
- CloudFront Distribution에서만 접근 허용

## 보안

- **Public Access Block**: 기본적으로 모든 Public Access 차단
- **암호화**: 기본값은 AES256, KMS Key 사용 가능
- **버전 관리**: 실수로 삭제된 파일 복구 가능

## 요구사항

- Terraform >= 1.6.0
- AWS Provider >= 5.0

## 참고

- 버킷 이름은 전 세계적으로 고유해야 합니다
- OAC는 CloudFront Distribution에서 사용됩니다
- 버킷 정책은 CloudFront Service Principal만 허용합니다
- 버전 관리가 활성화되면 스토리지 비용이 증가할 수 있습니다

