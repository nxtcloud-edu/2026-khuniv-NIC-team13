# ECS Module

이 모듈은 PERTINO 아키텍처를 위한 ECS (Elastic Container Service) 클러스터, 서비스, Task Definitions를 생성합니다. AWS Cloud Map을 사용한 서비스 디스커버리를 포함합니다.

## 기능

- ECS Cluster 생성 (Container Insights 활성화)
- Service Discovery (AWS Cloud Map) 설정
- IAM Roles (Task Execution Role, Task Role)
- Task Definitions (Service A, Service B)
- ECS Services (Fargate)
- CloudWatch Log Groups

## 사용법

```hcl
module "ecs" {
  source = "../../modules/ecs"

  cluster_name = "pertino-cluster"
  environment  = "dev"
  
  service_discovery_namespace_id = module.vpc.service_discovery_namespace_id
  subnet_ids                     = module.vpc.private_subnet_ids
  security_group_ids             = [module.vpc.ecs_security_group_id]
  dynamodb_table_arn            = module.dynamodb.table_arn
  ecr_repository_urls            = module.ecr.repository_urls
  
  service_a_config = {
    name          = "service-a"
    image         = ""
    cpu           = 256
    memory        = 512
    desired_count = 1
    port          = 8080
    environment_vars = {
      SERVICE_B_URL = "http://service-b.pertino.local:3000"
    }
  }
  
  service_b_config = {
    name          = "service-b"
    image         = ""
    cpu           = 512
    memory        = 1024
    desired_count = 1
    port          = 3000
    environment_vars = {
      ELASTICSEARCH_URL = "https://your-elasticsearch-endpoint.com"
      LLM_API_KEY       = "your-api-key"
    }
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
| `cluster_name` | ECS 클러스터 이름 | `string` | `"pertino-cluster"` | 아니오 |
| `service_a_config` | Service A 설정 | `object` | - | 예 |
| `service_b_config` | Service B 설정 | `object` | - | 예 |
| `service_discovery_namespace_id` | Service Discovery 네임스페이스 ID | `string` | - | 예 |
| `subnet_ids` | Private Subnet ID 리스트 | `list(string)` | - | 예 |
| `security_group_ids` | Security Group ID 리스트 | `list(string)` | - | 예 |
| `dynamodb_table_arn` | DynamoDB 테이블 ARN | `string` | - | 예 |
| `ecr_repository_urls` | ECR 리포지토리 URL 맵 | `map(string)` | `{}` | 아니오 |
| `task_execution_role_arn` | 기존 Task Execution Role ARN | `string` | `""` | 아니오 |
| `task_role_arn` | 기존 Task Role ARN | `string` | `""` | 아니오 |
| `project_name` | 프로젝트 이름 | `string` | `"pertino"` | 아니오 |
| `environment` | 환경 이름 (dev/prod) | `string` | - | 예 |
| `tags` | 추가 태그 | `map(string)` | `{}` | 아니오 |

### Service Config 객체 구조

```hcl
{
  name          = string  # 서비스 이름
  image         = string  # 컨테이너 이미지 (빈 문자열이면 ECR에서 가져옴)
  cpu           = number  # CPU 단위 (256, 512, 1024 등)
  memory        = number  # 메모리 (MB)
  desired_count = number  # 원하는 태스크 수
  port          = number  # 컨테이너 포트
  environment_vars = map(string)  # 환경 변수 맵
}
```

## 출력값

| 이름 | 설명 |
|------|------|
| `cluster_id` | ECS 클러스터 ID |
| `cluster_name` | ECS 클러스터 이름 |
| `cluster_arn` | ECS 클러스터 ARN |
| `service_a_name` | Service A 이름 |
| `service_b_name` | Service B 이름 |
| `service_a_service_discovery_name` | Service A Service Discovery DNS 이름 |
| `service_b_service_discovery_name` | Service B Service Discovery DNS 이름 |
| `service_discovery_namespace_id` | Service Discovery 네임스페이스 ID |
| `task_execution_role_arn` | Task Execution Role ARN |
| `task_role_arn` | Task Role ARN |

## 예시

### 기본 사용

```hcl
module "ecs" {
  source = "../../modules/ecs"

  environment                  = "dev"
  service_discovery_namespace_id = module.vpc.service_discovery_namespace_id
  subnet_ids                   = module.vpc.private_subnet_ids
  security_group_ids           = [module.vpc.ecs_security_group_id]
  dynamodb_table_arn           = module.dynamodb.table_arn
  ecr_repository_urls          = module.ecr.repository_urls
}
```

### 커스텀 설정

```hcl
module "ecs" {
  source = "../../modules/ecs"

  cluster_name = "my-cluster"
  environment  = "prod"
  
  service_a_config = {
    name          = "api-service"
    image         = "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-api:latest"
    cpu           = 512
    memory        = 1024
    desired_count = 2
    port          = 8080
    environment_vars = {
      DATABASE_URL = "postgresql://..."
      REDIS_URL    = "redis://..."
    }
  }
  
  service_b_config = {
    name          = "worker-service"
    image         = ""
    cpu           = 256
    memory        = 512
    desired_count = 1
    port          = 3000
    environment_vars = {}
  }
  
  # ... 나머지 설정
}
```

## Service Discovery

이 모듈은 AWS Cloud Map을 사용하여 서비스 간 통신을 가능하게 합니다:

- **Service A**: `service-a.pertino.local:8080`
- **Service B**: `service-b.pertino.local:3000`

서비스는 Private DNS 네임스페이스를 통해 서로를 찾을 수 있습니다.

**참고**: Service B는 ALB에 연결되지 않고 Service Discovery를 통해 Service A에서만 내부 통신으로 접근합니다.

## IAM Roles

### Task Execution Role
- ECR에서 이미지 가져오기
- CloudWatch Logs에 로그 전송

### Task Role
- DynamoDB 접근 (읽기/쓰기)

## 요구사항

- Terraform >= 1.6.0
- AWS Provider >= 5.0
- VPC 모듈 (Service Discovery 네임스페이스)
- ECR 모듈 (이미지 저장소)
- DynamoDB 모듈 (데이터베이스)

## 참고

- Fargate는 서버리스 컨테이너 실행 환경입니다
- Service Discovery를 통해 서비스 간 내부 통신이 가능합니다
- Private Subnet에 배치되며 Public IP는 할당되지 않습니다
- Service A는 ALB를 통해 외부에서 접근할 수 있습니다
- Service B는 ALB에 연결되지 않고 내부 통신(Service Discovery)만 사용합니다

