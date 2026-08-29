# Terraform Cloud 변수 설정 가이드

이 문서는 Terraform Cloud Workspace에 변수를 설정하는 방법을 설명합니다.

## Terraform Cloud UI에서 변수 설정

### 1. Workspace 접속

1. https://app.terraform.io 접속
2. Organization: `pertino` 선택
3. Workspace: `pertino-dev` (또는 `pertino-prod`) 선택

### 2. Variables 탭으로 이동

Workspace 페이지에서 **Variables** 탭을 클릭합니다.

### 3. 변수 추가

**Add variable** 버튼을 클릭하여 다음 변수들을 추가합니다:

#### 필수 변수

| Key | Value | Type | HCL | Sensitive |
|-----|-------|------|-----|-----------|
| `aws_region` | `ap-northeast-2` | `string` | ❌ | ❌ |
| `project_name` | `pertino` | `string` | ❌ | ❌ |
| `environment` | `dev` | `string` | ❌ | ❌ |

#### 선택 변수

| Key | Value | Type | HCL | Sensitive |
|-----|-------|------|-----|-----------|
| `domain_name` | (비워두거나 도메인 입력) | `string` | ❌ | ❌ |
| `enable_nat_gateway` | `true` | `bool` | ❌ | ❌ |
| `enable_vpc_endpoints` | `true` | `bool` | ❌ | ❌ |

### 4. 변수 타입별 설정

#### String 변수
- **Type**: `string`
- **HCL**: 체크 해제
- **Sensitive**: 민감 정보인 경우만 체크

#### Boolean 변수
- **Type**: `bool`
- **HCL**: 체크 해제
- **Value**: `true` 또는 `false`

#### Number 변수
- **Type**: `number`
- **HCL**: 체크 해제

### 5. 환경 변수 (선택사항)

AWS 자격 증명이 필요한 경우:

| Key | Value | Type | Sensitive |
|-----|-------|------|-----------|
| `AWS_ACCESS_KEY_ID` | (AWS Access Key) | `env` | ✅ |
| `AWS_SECRET_ACCESS_KEY` | (AWS Secret Key) | `env` | ✅ |

**주의**: AWS 자격 증명은 Terraform Cloud에서 AWS IAM Role을 사용하는 것을 권장합니다.

## terraform.auto.tfvars 파일 사용

로컬에서 테스트하거나 변수를 파일로 관리하고 싶은 경우:

1. `terraform.auto.tfvars.example` 파일을 참고하여 `terraform.auto.tfvars` 파일 생성
2. 변수 값 입력
3. **주의**: `terraform.auto.tfvars`는 Git에 커밋하지 마세요!

```hcl
# terraform/environments/dev/terraform.auto.tfvars
aws_region   = "ap-northeast-2"
project_name = "pertino"
environment  = "dev"
domain_name  = ""  # 비워두면 Route53 모듈이 생성되지 않음
enable_nat_gateway = true
enable_vpc_endpoints = true
```

## 변수 우선순위

1. **Terraform Cloud Workspace Variables** (UI에서 설정) - 최우선
2. `*.auto.tfvars` 파일
3. 변수의 기본값 (default)

## 참고

- Terraform Cloud UI에서 설정한 변수는 모든 실행에 적용됩니다
- `terraform.auto.tfvars` 파일은 Terraform Cloud에서도 자동으로 로드됩니다
- 민감한 정보는 반드시 **Sensitive**로 표시하세요

