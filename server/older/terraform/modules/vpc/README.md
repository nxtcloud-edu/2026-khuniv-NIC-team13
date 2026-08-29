# VPC Module

이 모듈은 PERTINO 아키텍처를 위한 VPC 네트워크 인프라를 생성합니다.

## 기능

- VPC 생성 (10.0.0.0/16)
- Public/Private Subnets (2개 AZ)
- Internet Gateway
- NAT Gateway (각 AZ별)
- VPC Endpoints (S3, DynamoDB, ECR, CloudWatch Logs)
- Security Groups (ALB, ECS, VPC Endpoints)

## 사용법

```hcl
module "vpc" {
  source = "../../modules/vpc"

  project_name = "pertino"
  environment  = "dev"
  
  vpc_cidr          = "10.0.0.0/16"
  availability_zones = ["ap-northeast-2a", "ap-northeast-2b"]
  
  enable_nat_gateway   = true
  enable_vpc_endpoints = true

  tags = {
    Environment = "dev"
    Project     = "pertino"
  }
}
```

## 변수

| 이름 | 설명 | 타입 | 기본값 | 필수 |
|------|------|------|--------|------|
| `vpc_cidr` | VPC CIDR 블록 | `string` | `"10.0.0.0/16"` | 아니오 |
| `availability_zones` | 가용 영역 리스트 | `list(string)` | `["ap-northeast-2a", "ap-northeast-2b"]` | 아니오 |
| `project_name` | 프로젝트 이름 | `string` | `"pertino"` | 아니오 |
| `environment` | 환경 이름 (dev/prod) | `string` | - | 예 |
| `enable_nat_gateway` | NAT Gateway 활성화 | `bool` | `true` | 아니오 |
| `enable_vpc_endpoints` | VPC Endpoints 활성화 | `bool` | `true` | 아니오 |
| `tags` | 추가 태그 | `map(string)` | `{}` | 아니오 |

## 출력값

| 이름 | 설명 |
|------|------|
| `vpc_id` | VPC ID |
| `vpc_cidr_block` | VPC CIDR 블록 |
| `public_subnet_ids` | Public Subnet ID 리스트 |
| `private_subnet_ids` | Private Subnet ID 리스트 |
| `nat_gateway_ids` | NAT Gateway ID 리스트 |
| `internet_gateway_id` | Internet Gateway ID |
| `alb_security_group_id` | ALB Security Group ID |
| `ecs_security_group_id` | ECS Security Group ID |
| `vpc_endpoint_ids` | VPC Endpoint ID 맵 |
| `vpc_endpoint_security_group_id` | VPC Endpoint Security Group ID |

## 예시

### 기본 사용

```hcl
module "vpc" {
  source = "../../modules/vpc"

  environment = "dev"
}
```

### 커스텀 설정

```hcl
module "vpc" {
  source = "../../modules/vpc"

  project_name  = "my-project"
  environment   = "prod"
  vpc_cidr      = "10.1.0.0/16"
  
  availability_zones = ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
  
  enable_nat_gateway   = true
  enable_vpc_endpoints = true

  tags = {
    Environment = "production"
    ManagedBy   = "terraform"
  }
}
```

## 네트워크 구조

```
VPC (10.0.0.0/16)
├── Public Subnets (2개 AZ)
│   ├── ap-northeast-2a: 10.0.0.0/24
│   └── ap-northeast-2b: 10.0.1.0/24
│       └── NAT Gateway (각 AZ별)
└── Private Subnets (2개 AZ)
    ├── ap-northeast-2a: 10.0.2.0/24
    └── ap-northeast-2b: 10.0.3.0/24
```

## VPC Endpoints

다음 VPC Endpoints가 생성됩니다:

- **S3 Gateway Endpoint**: S3 접근용
- **DynamoDB Gateway Endpoint**: DynamoDB 접근용
- **ECR Interface Endpoint**: ECR API 접근용
- **ECR DKR Interface Endpoint**: ECR Docker Registry 접근용
- **CloudWatch Logs Interface Endpoint**: CloudWatch Logs 접근용

## Security Groups

### ALB Security Group
- 인바운드: 포트 80, 443 (0.0.0.0/0)
- 아웃바운드: 모든 트래픽 허용

### ECS Security Group
- 인바운드: ALB Security Group에서만 접근 허용
- 아웃바운드: 모든 트래픽 허용

### VPC Endpoint Security Group
- 인바운드: 포트 443 (VPC 내부)
- 아웃바운드: 모든 트래픽 허용

## 요구사항

- Terraform >= 1.6.0
- AWS Provider >= 5.0

## 참고

- NAT Gateway는 시간당 요금이 발생합니다
- VPC Endpoints는 인터넷을 거치지 않고 AWS 서비스에 접근할 수 있게 해줍니다
- Private Subnets의 리소스는 NAT Gateway를 통해 인터넷에 접근할 수 있습니다

