# ECR Module

이 모듈은 PERTINO 아키텍처를 위한 ECR (Elastic Container Registry) 리포지토리를 생성합니다.

## 기능

- ECR Repository 생성 (Service A, Service B)
- Lifecycle Policy (이미지 보관 정책)
- Image Scanning (푸시 시 자동 스캔)
- 암호화 (AES256)

## 사용법

```hcl
module "ecr" {
  source = "../../modules/ecr"

  repository_names = ["pertino-service-a", "pertino-service-b"]
  environment      = "dev"
  
  image_tag_mutability = "MUTABLE"
  scan_on_push        = true
  max_image_count     = 10

  tags = {
    Environment = "dev"
    Project     = "pertino"
  }
}
```

## 변수

| 이름 | 설명 | 타입 | 기본값 | 필수 |
|------|------|------|--------|------|
| `repository_names` | ECR 리포지토리 이름 리스트 | `list(string)` | `["pertino-service-a", "pertino-service-b"]` | 아니오 |
| `image_tag_mutability` | 이미지 태그 변경 가능 여부 (MUTABLE/IMMUTABLE) | `string` | `"MUTABLE"` | 아니오 |
| `scan_on_push` | 푸시 시 이미지 스캔 활성화 | `bool` | `true` | 아니오 |
| `max_image_count` | 보관할 최대 이미지 수 | `number` | `10` | 아니오 |
| `project_name` | 프로젝트 이름 | `string` | `"pertino"` | 아니오 |
| `environment` | 환경 이름 (dev/prod) | `string` | - | 예 |
| `tags` | 추가 태그 | `map(string)` | `{}` | 아니오 |

## 출력값

| 이름 | 설명 |
|------|------|
| `repository_urls` | 리포지토리 URL 맵 |
| `repository_arns` | 리포지토리 ARN 맵 |
| `repository_names` | 리포지토리 이름 리스트 |
| `repository_registry_id` | 레지스트리 ID |

## 예시

### 기본 사용

```hcl
module "ecr" {
  source = "../../modules/ecr"

  environment = "dev"
}
```

### 커스텀 설정

```hcl
module "ecr" {
  source = "../../modules/ecr"

  repository_names = ["my-service-1", "my-service-2"]
  environment      = "prod"
  
  image_tag_mutability = "IMMUTABLE"
  scan_on_push        = true
  max_image_count     = 20

  tags = {
    Environment = "production"
    ManagedBy   = "terraform"
  }
}
```

## Lifecycle Policy

모듈은 자동으로 Lifecycle Policy를 생성하여 오래된 이미지를 정리합니다:

- 최대 이미지 수를 초과하는 이미지는 자동으로 삭제
- 기본값: 최대 10개 이미지 보관

## Image Scanning

- 푸시 시 자동으로 이미지 스캔
- 취약점 검사 수행
- AWS Security Hub와 통합 가능

## 요구사항

- Terraform >= 1.6.0
- AWS Provider >= 5.0

## 참고

- ECR 리포지토리는 리전별로 생성됩니다
- 이미지 스캔 결과는 ECR 콘솔에서 확인할 수 있습니다
- Lifecycle Policy는 즉시 적용됩니다

