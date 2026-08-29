# DynamoDB Module

이 모듈은 PERTINO 아키텍처를 위한 DynamoDB 테이블을 생성합니다.

## 기능

- DynamoDB 테이블 생성 (On-demand billing mode)
- Hash Key 및 Range Key 지원
- Point-in-time Recovery
- Server-side Encryption (AWS Managed 또는 KMS)

## 사용법

```hcl
module "dynamodb" {
  source = "../../modules/dynamodb"

  table_name = "pertino-data"
  hash_key   = "id"
  hash_key_type = "S"
  
  environment = "dev"
  
  enable_point_in_time_recovery = true
  enable_encryption             = true

  tags = {
    Environment = "dev"
    Project     = "pertino"
  }
}
```

## 변수

| 이름 | 설명 | 타입 | 기본값 | 필수 |
|------|------|------|--------|------|
| `table_name` | DynamoDB 테이블 이름 | `string` | - | 예 |
| `hash_key` | Hash (Partition) Key 속성 이름 | `string` | - | 예 |
| `hash_key_type` | Hash Key 타입 (S, N, B) | `string` | `"S"` | 아니오 |
| `range_key` | Range (Sort) Key 속성 이름 | `string` | `""` | 아니오 |
| `range_key_type` | Range Key 타입 (S, N, B) | `string` | `"S"` | 아니오 |
| `enable_point_in_time_recovery` | Point-in-time Recovery 활성화 | `bool` | `true` | 아니오 |
| `enable_encryption` | Server-side Encryption 활성화 | `bool` | `true` | 아니오 |
| `kms_key_id` | KMS Key ID (선택사항, 없으면 AWS Managed) | `string` | `null` | 아니오 |
| `project_name` | 프로젝트 이름 | `string` | `"pertino"` | 아니오 |
| `environment` | 환경 이름 (dev/prod) | `string` | - | 예 |
| `tags` | 추가 태그 | `map(string)` | `{}` | 아니오 |

## 출력값

| 이름 | 설명 |
|------|------|
| `table_id` | DynamoDB 테이블 ID |
| `table_arn` | DynamoDB 테이블 ARN |
| `table_name` | DynamoDB 테이블 이름 |
| `table_stream_arn` | DynamoDB Stream ARN (활성화된 경우) |
| `table_stream_label` | Stream 타임스탬프 |

## 예시

### 기본 사용 (Hash Key만)

```hcl
module "dynamodb" {
  source = "../../modules/dynamodb"

  table_name = "pertino-users"
  hash_key   = "userId"
  environment = "dev"
}
```

### Hash Key + Range Key

```hcl
module "dynamodb" {
  source = "../../modules/dynamodb"

  table_name     = "pertino-orders"
  hash_key       = "userId"
  hash_key_type  = "S"
  range_key      = "orderId"
  range_key_type = "S"
  environment    = "prod"
  
  enable_point_in_time_recovery = true
  enable_encryption             = true

  tags = {
    Environment = "production"
    ManagedBy   = "terraform"
  }
}
```

### KMS 암호화 사용

```hcl
module "dynamodb" {
  source = "../../modules/dynamodb"

  table_name = "pertino-sensitive-data"
  hash_key   = "id"
  environment = "prod"
  
  enable_encryption = true
  kms_key_id       = "arn:aws:kms:ap-northeast-2:123456789012:key/12345678-1234-1234-1234-123456789012"
}
```

## Billing Mode

이 모듈은 **On-demand (PAY_PER_REQUEST)** billing mode를 사용합니다:

- 용량 계획 불필요
- 사용한 만큼만 비용 지불
- 자동 스케일링

## Point-in-time Recovery

- 35일 이내의 특정 시점으로 복구 가능
- 백업 및 복구 전략의 일부
- 프로덕션 환경에서 권장

## 암호화

- 기본값: AWS Managed Key (AES256)
- 옵션: KMS Key 사용 가능
- 모든 데이터가 암호화되어 저장됨

## 요구사항

- Terraform >= 1.6.0
- AWS Provider >= 5.0

## 참고

- On-demand 모드는 용량 계획이 필요 없어 관리가 간편합니다
- Point-in-time Recovery는 추가 비용이 발생할 수 있습니다
- 테이블 이름은 리전 내에서 고유해야 합니다

