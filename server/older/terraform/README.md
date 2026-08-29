# PERTINO Terraform Infrastructure

PERTINO 아키텍처를 위한 AWS 인프라를 Terraform으로 관리하는 프로젝트입니다.

## 프로젝트 개요

이 프로젝트는 PERTINO 서비스를 위한 완전한 AWS 인프라를 Infrastructure as Code로 정의합니다.

### 주요 구성 요소

- **네트워크**: VPC, Subnets, NAT Gateway, VPC Endpoints
- **컴퓨팅**: ECS Fargate Cluster 및 Services
- **데이터베이스**: DynamoDB
- **스토리지**: S3 (Frontend 호스팅)
- **트래픽 관리**: ALB, CloudFront, Route53, WAF
- **컨테이너 레지스트리**: ECR

## 아키텍처

```
Internet
   ↓
CloudFront (WAF)
   ↓
   ├─ S3 (Frontend) - Default Behavior
   └─ ALB - /api/* Behavior
       ↓
       Service A (Spring Boot) - Port 8080
           ↓ (Internal via Service Discovery)
       Service B (FastAPI/LangChain) - Port 3000
           ↓
       DynamoDB
```

### 네트워크 구조

- **VPC**: 10.0.0.0/16 (ap-northeast-2)
- **Public Subnets**: NAT Gateway, ALB (2개 AZ)
- **Private Subnets**: ECS Workloads (2개 AZ)
- **VPC Endpoints**: DynamoDB, S3, ECR, CloudWatch Logs

### 서비스 디스커버리

- AWS Cloud Map을 사용하여 Service A와 Service B 간 내부 통신

## 모듈 구조

```
terraform/
├── modules/          # 재사용 가능한 모듈
│   ├── vpc/         # VPC 네트워크 구성
│   ├── ecr/         # ECR 리포지토리
│   ├── ecs/         # ECS Cluster 및 Services
│   ├── dynamodb/    # DynamoDB 테이블
│   ├── s3/          # S3 버킷 및 OAC
│   ├── alb/         # Application Load Balancer
│   ├── cloudfront/  # CloudFront Distribution
│   ├── route53/      # Route53 및 ACM
│   └── waf/         # WAF Web ACL
├── environments/     # 환경별 설정
│   ├── dev/         # 개발 환경
│   └── prod/        # 프로덕션 환경
└── shared/          # 공유 설정
    ├── providers.tf  # AWS Provider 설정
    └── remote-state.tf.example  # Remote State 예시
```

## 사용법

### 사전 요구사항

1. **Terraform 설치** (>= 1.6.0)
   ```bash
   terraform version
   ```

2. **AWS 자격 증명 설정**
   ```bash
   aws configure
   ```

3. **Terraform Cloud 설정**
   - Terraform Cloud 계정 생성
   - Organization 생성
   - Workspace 생성 (pertino-dev, pertino-prod)
   - `terraform login` 실행

### 환경별 배포

#### Dev 환경 배포

```bash
cd terraform/environments/dev

# Backend 초기화
terraform init

# 계획 확인
terraform plan

# 적용
terraform apply
```

#### Prod 환경 배포

```bash
cd terraform/environments/prod

# Backend 초기화
terraform init

# 계획 확인
terraform plan

# 적용
terraform apply
```

## Terraform Cloud 설정

### 변수 전달 방법

Terraform Cloud의 remote backend를 사용할 때 변수를 전달하는 방법은 다음과 같습니다:

#### 방법 1: Terraform Cloud UI에서 설정 (권장)

1. Terraform Cloud 웹 콘솔 접속: https://app.terraform.io
2. Organization 선택 → Workspace 선택 (예: `pertino-dev`)
3. **Variables** 탭으로 이동
4. **Add variable** 클릭
5. 변수 추가:
   - **Key**: 변수 이름 (예: `domain_name`)
   - **Value**: 변수 값 (예: `example.com`)
   - **Type**: `string`, `number`, `bool` 등
   - **HCL**: HCL 형식 사용 여부
   - **Sensitive**: 민감 정보인 경우 체크

**예시 변수**:
- `aws_region` = `ap-northeast-2`
- `project_name` = `pertino`
- `environment` = `dev`
- `domain_name` = `example.com` (선택사항)
- `enable_nat_gateway` = `true`
- `enable_vpc_endpoints` = `true`

#### 방법 2: `*.auto.tfvars` 파일 사용

`terraform.auto.tfvars` 파일을 생성하면 Terraform Cloud에서 자동으로 로드됩니다:

```hcl
# terraform/environments/dev/terraform.auto.tfvars
aws_region   = "ap-northeast-2"
project_name = "pertino"
environment  = "dev"
domain_name  = ""  # 비워두면 Route53 모듈이 생성되지 않음
enable_nat_gateway = true
enable_vpc_endpoints = true
```

**주의사항**:
- `terraform.auto.tfvars` 파일은 Git에 커밋하지 마세요 (민감 정보 포함 가능)
- `.gitignore`에 이미 포함되어 있습니다
- `terraform.auto.tfvars.example` 파일을 참고하세요

#### 방법 3: CLI로 변수 설정 (로컬 실행 시)

로컬에서 실행할 때는 `-var` 옵션을 사용할 수 없습니다 (remote backend 사용 시).
대신 `terraform.auto.tfvars` 파일을 사용하거나 Terraform Cloud UI에서 설정해야 합니다.

### 변수 우선순위

1. Terraform Cloud Workspace Variables (UI에서 설정)
2. `*.auto.tfvars` 파일
3. 변수의 기본값 (default)

## Terraform Cloud 설정 가이드

### 1. Organization 및 Workspace 생성

1. [Terraform Cloud](https://app.terraform.io)에 로그인
2. Organization 생성 (예: `pertino-org`)
3. Workspace 생성:
   - **pertino-dev** (CLI-Driven Workflow)
   - **pertino-prod** (CLI-Driven Workflow)

### 2. 로컬 인증 설정

```bash
terraform login
```

또는 `~/.terraform.d/credentials.tfrc.json` 파일에 토큰 저장:

```json
{
  "credentials": {
    "app.terraform.io": {
      "token": "your-token-here"
    }
  }
}
```

### 3. Backend 설정

각 환경의 `backend.tf` 파일에서 Terraform Cloud 백엔드를 설정합니다:

```hcl
terraform {
  cloud {
    organization = "pertino"

    workspaces {
      name = "pertino-dev"  # or pertino-prod
    }
  }
}
```

**참고**: Terraform 1.6.0 이상에서는 `cloud` 블록을 사용합니다. 이전 버전에서는 `backend "remote"`를 사용합니다.

## 변수 관리

### 필수 변수

- `domain_name`: Route53 도메인 이름
- `acm_certificate_arn`: SSL 인증서 ARN (선택사항, Route53 모듈에서 생성 가능)

### 환경 변수

민감한 정보는 환경 변수로 관리:

```bash
export TF_VAR_llm_api_key="your-api-key"
export TF_VAR_elasticsearch_endpoint="your-endpoint"
```

### Terraform Cloud Variables

Terraform Cloud UI에서 Workspace Variables로 관리하거나 `terraform.tfvars` 파일 사용 (Git에 커밋하지 않음)

## 주의사항

1. **민감 정보 관리**
   - `*.tfvars` 파일은 절대 Git에 커밋하지 않음
   - `.tfvars.example`만 커밋
   - 실제 값은 환경 변수나 Terraform Cloud Variables 사용

2. **State 파일**
   - Terraform Cloud에서 자동 관리
   - 로컬 State 파일은 `.gitignore`에 포함

3. **모듈 의존성**
   - VPC → ECS, ALB
   - ECR → ECS
   - DynamoDB → ECS
   - S3, ALB, WAF → CloudFront
   - CloudFront → Route53

4. **비용 관리**
   - NAT Gateway는 시간당 요금 발생
   - CloudFront Price Class 설정으로 비용 최적화
   - Dev 환경에서는 불필요한 리소스 제거 고려

## 개발 가이드

### 모듈 추가

1. `terraform/modules/<module-name>/` 디렉토리 생성
2. `main.tf`, `variables.tf`, `outputs.tf`, `README.md` 작성
3. `environments/*/main.tf`에서 모듈 호출 추가

### 모듈 테스트

```bash
cd terraform/modules/<module-name>
terraform init
terraform validate
terraform fmt
```

## 문제 해결

### Terraform Cloud 연결 실패

```bash
terraform logout
terraform login
```

### Provider 버전 충돌

`.terraform.lock.hcl` 파일을 확인하고 필요시 업데이트:

```bash
terraform init -upgrade
```

## 참고 자료

- [Terraform AWS Provider 문서](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform Cloud 문서](https://developer.hashicorp.com/terraform/cloud-docs)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)

