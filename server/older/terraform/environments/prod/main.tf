# VPC Module
module "vpc" {
  source = "../../modules/vpc"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = "10.0.0.0/16"
  availability_zones = ["ap-northeast-2a", "ap-northeast-2b"]

  enable_nat_gateway             = var.enable_nat_gateway
  nat_type                       = "instance"  # NAT Instance 사용 (비용 절감)
  nat_instance_type              = "t4g.micro" # 프로덕션 환경용 (더 높은 처리량)
  nat_instance_count             = 1
  enable_vpc_endpoints           = var.enable_vpc_endpoints
  enable_vpc_interface_endpoints = var.enable_vpc_interface_endpoints

  # Security: Restrict ALB to CloudFront only (blocks direct ALB access)
  restrict_alb_to_cloudfront = var.restrict_alb_to_cloudfront

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECR Module
module "ecr" {
  source = "../../modules/ecr"

  project_name = var.project_name
  environment  = var.environment

  repository_names     = ["pertino-service-a", "pertino-service-b"]
  image_tag_mutability = "MUTABLE"
  scan_on_push         = true
  max_image_count      = 10

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# DynamoDB Module - Lock Table (분산 락)
module "dynamodb_lock" {
  source = "../../modules/dynamodb"

  project_name = var.project_name
  environment  = var.environment

  table_name    = "${var.project_name}-${var.environment}-lock"
  hash_key      = "lock_key"
  hash_key_type = "S"

  ttl_attribute                 = "ttl"
  enable_point_in_time_recovery = false
  enable_encryption             = true

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "distributed-lock"
  }
}

# DynamoDB Module - Access Code Table (인증 코드)
module "dynamodb_access_code" {
  source = "../../modules/dynamodb"

  project_name = var.project_name
  environment  = var.environment

  table_name    = "${var.project_name}-${var.environment}-access-code"
  hash_key      = "access_code_key"
  hash_key_type = "S"

  ttl_attribute                 = "ttl"
  enable_point_in_time_recovery = true
  enable_encryption             = true

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "access-code"
  }
}

# DynamoDB Module - Popup Table (팝업 데이터)
module "dynamodb_popup" {
  source = "../../modules/dynamodb"

  project_name = var.project_name
  environment  = var.environment

  table_name    = "${var.project_name}-${var.environment}-popup"
  hash_key      = "id"
  hash_key_type = "S"

  ttl_attribute                 = null
  enable_point_in_time_recovery = true
  enable_encryption             = true

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "popup"
  }
}

# DynamoDB Module - Notice Table (공지사항)
module "dynamodb_notice" {
  source = "../../modules/dynamodb"

  project_name = var.project_name
  environment  = var.environment

  table_name    = "${var.project_name}-${var.environment}-notice"
  hash_key      = "id"
  hash_key_type = "S"

  ttl_attribute                 = null
  enable_point_in_time_recovery = true
  enable_encryption             = true

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "notice"
  }
}

# DynamoDB Module - Email Table (이메일 정보)
module "dynamodb_email" {
  source = "../../modules/dynamodb"

  project_name = var.project_name
  environment  = var.environment

  table_name    = "${var.project_name}-${var.environment}-email"
  hash_key      = "email"
  hash_key_type = "S"

  ttl_attribute                 = null
  enable_point_in_time_recovery = true
  enable_encryption             = true

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "email"
  }
}

# DynamoDB Module - Admin Table (관리자 목록)
module "dynamodb_admin" {
  source = "../../modules/dynamodb"

  project_name = var.project_name
  environment  = var.environment

  table_name    = "${var.project_name}-${var.environment}-admin"
  hash_key      = "email"
  hash_key_type = "S"

  ttl_attribute                 = null
  enable_point_in_time_recovery = true
  enable_encryption             = true

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "admin"
  }
}

# DynamoDB Module - Properties Table (서비스 설정)
module "dynamodb_properties" {
  source = "../../modules/dynamodb"

  project_name = var.project_name
  environment  = var.environment

  table_name    = "${var.project_name}-${var.environment}-properties"
  hash_key      = "id"
  hash_key_type = "S"

  ttl_attribute                 = null
  enable_point_in_time_recovery = true
  enable_encryption             = true

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "properties"
  }
}

# DynamoDB Module - WhiteList Table (화이트리스트)
module "dynamodb_whitelist" {
  source = "../../modules/dynamodb"

  project_name = var.project_name
  environment  = var.environment

  table_name    = "${var.project_name}-${var.environment}-whitelist"
  hash_key      = "email"
  hash_key_type = "S"

  ttl_attribute                 = null
  enable_point_in_time_recovery = true
  enable_encryption             = true

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "whitelist"
  }
}

# DynamoDB Module - Member Documents (멤버 약관 등 문서)
module "dynamodb_member_documents" {
  source = "../../modules/dynamodb"

  project_name = var.project_name
  environment  = var.environment

  table_name     = "${var.project_name}-${var.environment}-member-documents"
  hash_key       = "pk"
  hash_key_type  = "S"
  range_key      = "sk"
  range_key_type = "S"

  ttl_attribute                 = null
  enable_point_in_time_recovery = true
  enable_encryption             = true

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "member-documents"
  }
}

# DynamoDB Module - Sessions (세션, email GSI)
module "dynamodb_sessions" {
  source = "../../modules/dynamodb"

  project_name = var.project_name
  environment  = var.environment

  table_name    = "${var.project_name}-${var.environment}-sessions"
  hash_key      = "session_id"
  hash_key_type = "S"

  ttl_attribute                 = "ttl"
  enable_point_in_time_recovery = true
  enable_encryption             = true

  global_secondary_indexes = [
    {
      name            = "email-index"
      hash_key        = "email"
      hash_key_type   = "S"
      range_key       = ""
      range_key_type  = "S"
      projection_type = "ALL"
    }
  ]

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "sessions"
  }
}

# S3 Module
module "s3" {
  source = "../../modules/s3"

  project_name = var.project_name
  environment  = var.environment

  bucket_name = "${var.project_name}-${var.environment}-frontend"

  enable_versioning   = true
  enable_encryption   = true
  block_public_access = true

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

data "aws_dynamodb_table" "service_b_document_context" {
  name = "pertineo-document-context"
}

locals {
  service_b_s3_vector_bucket_arns = [
    "arn:aws:s3vectors:${var.aws_region}:${data.aws_caller_identity.current.account_id}:bucket/pertineo-data-vector",
    "arn:aws:s3vectors:${var.aws_region}:${data.aws_caller_identity.current.account_id}:bucket/pertineo-data-vector-index"
  ]
}

# ALB Module
module "alb" {
  source = "../../modules/alb"

  name         = "pertino-alb"
  project_name = var.project_name
  environment  = var.environment

  subnet_ids        = module.vpc.public_subnet_ids
  security_group_id = module.vpc.alb_security_group_id
  certificate_arn   = var.domain_name != "" ? module.route53.alb_certificate_arn : var.alb_certificate_arn

  service_a_target_group_config = {
    port                  = 8080
    protocol              = "HTTP"
    health_check_path     = "/actuator/health"
    health_check_port     = 8080
    health_check_protocol = "HTTP"
    timeout               = 120 # health check 제한시간 120초
    interval              = 130 # interval > timeout 권장
  }

  enable_http_redirect       = true
  enable_deletion_protection = true

  # Blue/Green Deployment: Enable green target group and test listener
  enable_blue_green  = true
  test_listener_port = 8443

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECS Module
module "ecs" {
  source = "../../modules/ecs"

  cluster_name = "${var.project_name}-cluster"
  project_name = var.project_name
  environment  = var.environment

  service_discovery_namespace_id = module.vpc.vpc_id                  # VPC ID를 사용하여 네임스페이스 생성
  subnet_ids                     = [module.vpc.private_subnet_ids[0]] # 단일 AZ(ap-northeast-2a)에서만 ECS 태스크 실행
  security_group_ids             = [module.vpc.ecs_security_group_id]
  dynamodb_table_arns = [
    module.dynamodb_lock.table_arn,
    module.dynamodb_access_code.table_arn,
    module.dynamodb_popup.table_arn,
    module.dynamodb_notice.table_arn,
    module.dynamodb_email.table_arn,
    module.dynamodb_admin.table_arn,
    module.dynamodb_properties.table_arn,
    module.dynamodb_whitelist.table_arn,
    module.dynamodb_member_documents.table_arn,
    module.dynamodb_sessions.table_arn,
    "${module.dynamodb_sessions.table_arn}/index/*",
    data.aws_dynamodb_table.service_b_document_context.arn
  ]
  s3_vector_bucket_arns = local.service_b_s3_vector_bucket_arns
  ecr_repository_urls   = module.ecr.repository_urls

  service_a_target_group_arn = module.alb.service_a_target_group_arn
  service_b_target_group_arn = "" # service-b는 ALB에 연결하지 않음 (내부 통신만 사용)

  # Auto Scaling Configuration
  alb_arn_suffix                    = module.alb.alb_arn_suffix
  service_a_target_group_arn_suffix = module.alb.service_a_target_group_arn_suffix

  service_a_autoscaling = {
    min_capacity = 1
    max_capacity = 4
  }
  service_b_autoscaling = {
    min_capacity = 1
    max_capacity = 4
  }

  # Blue/Green Deployment Configuration
  enable_blue_green = true
  blue_green_config = {
    prod_listener_arn                = module.alb.https_listener_arn
    test_listener_arn                = module.alb.test_listener_arn
    blue_target_group_name           = module.alb.service_a_target_group_name
    green_target_group_name          = module.alb.service_a_green_target_group_name
    deployment_config_name           = "CodeDeployDefault.ECSAllAtOnce"
    termination_wait_time_in_minutes = 5
  }

  # Ensure ALB listener rules are created before ECS tries to attach target groups
  depends_on = [module.alb]

  service_a_config = {
    name          = "service-a"
    image         = ""
    cpu           = 256
    memory        = 512
    desired_count = 1
    port          = 8080
    environment_vars = {
      # Spring 프로필 설정 (프로덕션 환경)
      SPRING_PROFILES_ACTIVE = "prod"

      SERVICE_B_URL = "http://service-b.pertino.local:8080"

      DYNAMODB_LOCK_TABLE_NAME             = module.dynamodb_lock.table_name
      DYNAMODB_ACCESS_CODE_TABLE_NAME      = module.dynamodb_access_code.table_name
      DYNAMODB_POPUP_TABLE_NAME            = module.dynamodb_popup.table_name
      DYNAMODB_NOTICE_TABLE_NAME           = module.dynamodb_notice.table_name
      DYNAMODB_EMAIL_TABLE_NAME            = module.dynamodb_email.table_name
      DYNAMODB_ADMIN_TABLE_NAME            = module.dynamodb_admin.table_name
      DYNAMODB_PROPERTIES_TABLE_NAME       = module.dynamodb_properties.table_name
      DYNAMODB_WHITELIST_TABLE_NAME        = module.dynamodb_whitelist.table_name
      DYNAMODB_MEMBER_DOCUMENTS_TABLE_NAME = module.dynamodb_member_documents.table_name
      DYNAMODB_SESSIONS_TABLE_NAME         = module.dynamodb_sessions.table_name
      DYNAMODB_NOTICE_TABLE_NAME           = module.dynamodb_notice.table_name
      DYNAMODB_EMAIL_TABLE_NAME            = module.dynamodb_email.table_name
      DYNAMODB_ADMIN_TABLE_NAME            = module.dynamodb_admin.table_name
      DYNAMODB_PROPERTIES_TABLE_NAME       = module.dynamodb_properties.table_name
      DYNAMODB_WHITELIST_TABLE_NAME        = module.dynamodb_whitelist.table_name

      # Database configuration (deprecated - using DynamoDB)
      # SPRING_DATASOURCE_URL      = "jdbc:mysql://pertineo1234.cnckke2e25n9.ap-northeast-2.rds.amazonaws.com:3306/dev?serverTimezone=Asia/Seoul&characterEncoding=UTF-8"
      # SPRING_DATASOURCE_USERNAME = "admin"

      # Mail configuration
      SPRING_MAIL_HOST     = "smtp.gmail.com"
      SPRING_MAIL_PORT     = "587"
      SPRING_MAIL_USERNAME = "pertineo.yskim@gmail.com"

      # OAuth configuration
      SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_GOOGLE_CLIENT_ID = "585939641747-5hq5tukepcb0k8s2r5h1910iec0rj8v0.apps.googleusercontent.com"

      # Redis configuration (optional, defaults to localhost:6379 if not set)
      # SPRING_REDIS_HOST = "localhost"
      # SPRING_REDIS_PORT = "6379"

      # CORS configuration
      CORS_ALLOWED_ORIGINS = "https://pertineo.khu.ac.kr,https://pertineo.vercel.app,https://pertineo-test.vercel.app,http://localhost:3000,http://localhost:8080,https://khu-pertineo-deploy.com,https://pertineo-weld.vercel.app"
    }
    # Secrets from AWS Secrets Manager
    secrets = {
      SPRING_DATASOURCE_PASSWORD                                      = "arn:aws:secretsmanager:ap-northeast-2:055292472277:secret:pertino-prod/db-password-qks2yd"
      SPRING_MAIL_PASSWORD                                            = "arn:aws:secretsmanager:ap-northeast-2:055292472277:secret:pertino-prod/mail-password-KRkMSG"
      CHATGPT_API_KEY                                                 = "arn:aws:secretsmanager:ap-northeast-2:055292472277:secret:pertino-prod/chatgpt-api-key-LhAKng"
      SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_GOOGLE_CLIENT_SECRET = "arn:aws:secretsmanager:ap-northeast-2:055292472277:secret:pertino-prod/google-client-secret-AnwUKO"
      SPRING_JWT_SECRET                                               = "arn:aws:secretsmanager:ap-northeast-2:055292472277:secret:pertino-prod/jwt-secret-YySjl2"
      ANALYSIS_SERVICE_BASE_URL                                       = aws_secretsmanager_secret.service_a_analysis_service_base_url.arn
    }
  }

  service_b_config = {
    name          = "service-b"
    image         = ""
    cpu           = 256
    memory        = 1024
    desired_count = 1
    port          = 8080
    environment_vars = {
      AWS_REGION             = "ap-northeast-2"
      LANGSMITH_PROJECT      = "pertineo-prod"
      SPRING_PROFILES_ACTIVE = "prod"
    }
    secrets = {
      OPENAI_API_KEY    = aws_secretsmanager_secret.service_b_openai_key.arn
      LANGSMITH_API_KEY = aws_secretsmanager_secret.service_b_langsmith_key.arn
      TAVILY_API_KEY    = aws_secretsmanager_secret.service_b_tavily_key.arn
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# WAF Module
module "waf" {
  source = "../../modules/waf"

  name         = "pertino-waf"
  scope        = "CLOUDFRONT"
  project_name = var.project_name
  environment  = var.environment

  enable_rate_limiting = true
  rate_limit           = 5000

  enable_geo_blocking = false

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudFront Module
module "cloudfront" {
  source = "../../modules/cloudfront"

  project_name = var.project_name
  environment  = var.environment

  aliases = var.domain_name != "" ? [var.domain_name] : []

  s3_origin_config = {
    bucket_regional_domain_name = module.s3.bucket_regional_domain_name
    bucket_id                   = module.s3.bucket_id
    oac_id                      = module.s3.oac_id
  }

  alb_origin_config = {
    alb_dns_name = module.alb.alb_dns_name
    alb_zone_id  = module.alb.alb_zone_id
  }

  certificate_arn = var.domain_name != "" ? module.route53.cloudfront_certificate_arn : ""
  waf_web_acl_arn = module.waf.web_acl_arn

  price_class = "PriceClass_All"

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Get current AWS account ID (for CloudFront OAC bucket policy)
data "aws_caller_identity" "current" {}

# S3 Bucket Policy for CloudFront OAC (lock to specific distribution)
resource "aws_s3_bucket_policy" "frontend_cloudfront_oac" {
  bucket = module.s3.bucket_id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${module.s3.bucket_arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = "arn:aws:cloudfront::${data.aws_caller_identity.current.account_id}:distribution/${module.cloudfront.distribution_id}"
          }
        }
      }
    ]
  })

  depends_on = [module.s3, module.cloudfront]
}

# Route53 Module
module "route53" {
  source = "../../modules/route53"

  domain_name                = var.domain_name
  cloudfront_distribution_id = module.cloudfront.distribution_id
  project_name               = var.project_name
  environment                = var.environment

  # Hosted Zone: create new or use existing
  create_hosted_zone      = var.domain_name != "" && var.create_hosted_zone
  existing_hosted_zone_id = var.existing_hosted_zone_id

  # ACM certificates: CloudFront (us-east-1) and ALB (ap-northeast-2)
  create_acm_certificate = var.domain_name != ""

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Grafana Alloy Module (scrapes Prometheus metrics → Grafana Cloud)
module "grafana_alloy" {
  source = "../../modules/grafana-alloy"

  project_name = var.project_name
  environment  = var.environment

  cluster_id         = module.ecs.cluster_id
  subnet_ids         = [module.vpc.private_subnet_ids[0]]
  security_group_ids = [module.vpc.ecs_security_group_id]

  grafana_cloud_secret_arns = {
    prometheus_endpoint = aws_secretsmanager_secret.grafana_cloud_prometheus_endpoint.arn
    prometheus_username = aws_secretsmanager_secret.grafana_cloud_prometheus_username.arn
    api_key             = aws_secretsmanager_secret.grafana_cloud_api_key.arn
  }

  scrape_targets = [
    {
      name            = "service_a"
      address         = "service-a.pertino.local:8080"
      metrics_path    = "/actuator/prometheus"
      scrape_interval = "15s"
    }
  ]

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Dashboard Module
module "cloudwatch_dashboard" {
  source = "../../modules/cloudwatch-dashboard"

  project_name   = var.project_name
  environment    = var.environment
  dashboard_name = "Pertineo-monitor"

  # ECS Configuration
  cluster_name   = module.ecs.cluster_name
  service_a_name = "service-a"
  service_b_name = "service-b"

  # ALB Configuration
  alb_arn_suffix          = module.alb.alb_arn_suffix
  target_group_arn_suffix = module.alb.service_a_target_group_arn_suffix

  # DynamoDB Tables
  dynamodb_table_names = [
    module.dynamodb_lock.table_name,
    module.dynamodb_access_code.table_name,
    module.dynamodb_popup.table_name,
    module.dynamodb_notice.table_name,
    module.dynamodb_email.table_name,
    module.dynamodb_admin.table_name,
    module.dynamodb_properties.table_name,
    module.dynamodb_whitelist.table_name
  ]

  # CloudWatch Logs
  service_a_log_group = module.ecs.service_a_log_group_name
  service_b_log_group = module.ecs.service_b_log_group_name

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Security Group Rule for Blue/Green Test Listener (port 8443)
# Allows test traffic to reach the green target group for validation
resource "aws_security_group_rule" "alb_test_listener" {
  type              = "ingress"
  from_port         = 8443
  to_port           = 8443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = module.vpc.alb_security_group_id
  description       = "Allow test traffic for blue/green deployment validation"
}
