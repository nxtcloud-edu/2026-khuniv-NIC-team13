# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = var.cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(
    var.tags,
    {
      Name        = var.cluster_name
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# Service Discovery Private DNS Namespace
resource "aws_service_discovery_private_dns_namespace" "main" {
  name        = "${var.project_name}.local"
  description = "Service discovery namespace for ${var.cluster_name}"
  # Use explicit VPC ID input to avoid "known after apply" churn
  # (data lookup via subnet can become unknown and force replacement)
  vpc = var.service_discovery_namespace_id

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-service-discovery"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# ECS Task Execution Role
resource "aws_iam_role" "task_execution" {
  count = var.task_execution_role_arn == "" ? 1 : 0

  name = "${var.project_name}-${var.environment}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-ecs-task-execution-role"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# Attach AWS managed policy for Task Execution Role
resource "aws_iam_role_policy_attachment" "task_execution" {
  count = var.task_execution_role_arn == "" ? 1 : 0

  role       = aws_iam_role.task_execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Task Execution Role Policy for ECR and CloudWatch Logs
resource "aws_iam_role_policy" "task_execution" {
  count = var.task_execution_role_arn == "" ? 1 : 0

  name = "${var.project_name}-${var.environment}-ecs-task-execution-policy"
  role = aws_iam_role.task_execution[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "*"
      }
    ]
  })
}

# ECS Task Role
resource "aws_iam_role" "task" {
  count = var.task_role_arn == "" ? 1 : 0

  name = "${var.project_name}-${var.environment}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-ecs-task-role"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# Task Role Policy for DynamoDB access
resource "aws_iam_role_policy" "task" {
  count = var.task_role_arn == "" ? 1 : 0

  name = "${var.project_name}-${var.environment}-ecs-task-policy"
  role = aws_iam_role.task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Effect = "Allow"
          Action = [
            "dynamodb:GetItem",
            "dynamodb:PutItem",
            "dynamodb:UpdateItem",
            "dynamodb:DeleteItem",
            "dynamodb:Query",
            "dynamodb:Scan"
          ]
          Resource = var.dynamodb_table_arns
        },
        {
          Effect = "Allow"
          Action = [
            "cloudwatch:PutMetricData"
          ]
          Resource = "*"
        },
        # ECS Exec uses SSM message channels from inside the task
        {
          Effect = "Allow"
          Action = [
            "ssmmessages:CreateControlChannel",
            "ssmmessages:CreateDataChannel",
            "ssmmessages:OpenControlChannel",
            "ssmmessages:OpenDataChannel"
          ]
          Resource = "*"
        }
      ],
      length(var.s3_bucket_arns) > 0 ? [
        {
          Effect = "Allow"
          Action = [
            "s3:ListBucket"
          ]
          Resource = var.s3_bucket_arns
        },
        {
          Effect = "Allow"
          Action = [
            "s3:GetObject",
            "s3:PutObject",
            "s3:DeleteObject"
          ]
          Resource = [for bucket_arn in var.s3_bucket_arns : "${bucket_arn}/*"]
        }
      ] : [],
      length(var.s3_vector_bucket_arns) > 0 ? [
        {
          Effect = "Allow"
          Action = [
            "s3vectors:GetVectorBucket",
            "s3vectors:ListIndexes"
          ]
          Resource = var.s3_vector_bucket_arns
        },
        {
          Effect = "Allow"
          Action = [
            "s3vectors:GetIndex",
            "s3vectors:QueryVectors",
            "s3vectors:GetVectors",
            "s3vectors:PutVectors",
            "s3vectors:DeleteVectors",
            "s3vectors:ListVectors"
          ]
          Resource = [for bucket_arn in var.s3_vector_bucket_arns : "${bucket_arn}/index/*"]
        }
      ] : []
    )
  })
}

# Get role ARNs
locals {
  task_execution_role_arn = var.task_execution_role_arn != "" ? var.task_execution_role_arn : aws_iam_role.task_execution[0].arn
  task_role_arn           = var.task_role_arn != "" ? var.task_role_arn : aws_iam_role.task[0].arn
}

# CodeDeploy IAM Role for ECS Blue/Green Deployment
resource "aws_iam_role" "codedeploy" {
  count = var.enable_blue_green ? 1 : 0

  name = "${var.project_name}-${var.environment}-codedeploy-ecs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codedeploy.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-codedeploy-ecs-role"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# Attach AWS managed policy for CodeDeploy ECS
resource "aws_iam_role_policy_attachment" "codedeploy" {
  count = var.enable_blue_green ? 1 : 0

  role       = aws_iam_role.codedeploy[0].name
  policy_arn = "arn:aws:iam::aws:policy/AWSCodeDeployRoleForECS"
}

# CodeDeploy Application for ECS
resource "aws_codedeploy_app" "service_a" {
  count = var.enable_blue_green ? 1 : 0

  name             = "${var.project_name}-${var.environment}-service-a"
  compute_platform = "ECS"

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-service-a-codedeploy"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# CodeDeploy Deployment Group for ECS Blue/Green
resource "aws_codedeploy_deployment_group" "service_a" {
  count = var.enable_blue_green ? 1 : 0

  app_name               = aws_codedeploy_app.service_a[0].name
  deployment_group_name  = "${var.project_name}-${var.environment}-service-a-dg"
  service_role_arn       = aws_iam_role.codedeploy[0].arn
  deployment_config_name = var.blue_green_config.deployment_config_name

  deployment_style {
    deployment_option = "WITH_TRAFFIC_CONTROL"
    deployment_type   = "BLUE_GREEN"
  }

  blue_green_deployment_config {
    deployment_ready_option {
      action_on_timeout    = "STOP_DEPLOYMENT"
      wait_time_in_minutes = 2880  # 48시간 대기 (AWS 최대값, 수동 continue-deployment까지)
    }

    terminate_blue_instances_on_deployment_success {
      action                           = "TERMINATE"
      termination_wait_time_in_minutes = var.blue_green_config.termination_wait_time_in_minutes
    }
  }

  ecs_service {
    cluster_name = aws_ecs_cluster.main.name
    service_name = aws_ecs_service.service_a.name
  }

  load_balancer_info {
    target_group_pair_info {
      prod_traffic_route {
        listener_arns = [var.blue_green_config.prod_listener_arn]
      }

      test_traffic_route {
        listener_arns = [var.blue_green_config.test_listener_arn]
      }

      target_group {
        name = var.blue_green_config.blue_target_group_name
      }

      target_group {
        name = var.blue_green_config.green_target_group_name
      }
    }
  }

  auto_rollback_configuration {
    enabled = true
    events  = ["DEPLOYMENT_FAILURE", "DEPLOYMENT_STOP_ON_REQUEST"]
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-service-a-deployment-group"
      Environment = var.environment
      Project     = var.project_name
    }
  )

  depends_on = [
    aws_ecs_service.service_a
  ]
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "service_a" {
  name              = "/ecs/${var.cluster_name}/${var.service_a_config.name}"
  retention_in_days = 7

  tags = merge(
    var.tags,
    {
      Name        = "${var.cluster_name}-${var.service_a_config.name}-logs"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

resource "aws_cloudwatch_log_group" "service_b" {
  name              = "/ecs/${var.cluster_name}/${var.service_b_config.name}"
  retention_in_days = 7

  tags = merge(
    var.tags,
    {
      Name        = "${var.cluster_name}-${var.service_b_config.name}-logs"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# Service Discovery Services
resource "aws_service_discovery_service" "service_a" {
  name = var.service_a_config.name
  # Prevent delete failures when instances are still registered (ECS tasks)
  force_destroy = true

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  # Health check configuration for ECS tasks
  # ECS automatically manages health status - unhealthy tasks are removed from DNS
  # failure_threshold: number of 30-second intervals that health checker waits before changing status
  health_check_custom_config {
    failure_threshold = 1
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.service_a_config.name}-discovery"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

resource "aws_service_discovery_service" "service_b" {
  name = var.service_b_config.name
  # Prevent delete failures when instances are still registered (ECS tasks)
  force_destroy = true

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  # Health check configuration for ECS tasks
  # ECS automatically manages health status - unhealthy tasks are removed from DNS
  # failure_threshold: number of 30-second intervals that health checker waits before changing status
  health_check_custom_config {
    failure_threshold = 1
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.service_b_config.name}-discovery"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# ECS Task Definitions
resource "aws_ecs_task_definition" "service_a" {
  family                   = "${var.project_name}-${var.environment}-${var.service_a_config.name}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.service_a_config.cpu
  memory                   = var.service_a_config.memory
  execution_role_arn       = local.task_execution_role_arn
  task_role_arn            = local.task_role_arn

  container_definitions = jsonencode([
    {
      name      = var.service_a_config.name
      image     = var.service_a_config.image != "" ? var.service_a_config.image : "${var.ecr_repository_urls["pertino-service-a"]}:latest"
      essential = true

      portMappings = [
        {
          containerPort = var.service_a_config.port
          protocol      = "tcp"
        }
      ]

      environment = [
        for key, value in var.service_a_config.environment_vars : {
          name  = key
          value = value
        }
      ]

      secrets = length(var.service_a_config.secrets) > 0 ? [
        for env_var_name, secret_arn in var.service_a_config.secrets : {
          name      = env_var_name
          valueFrom = secret_arn
        }
      ] : []

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.service_a.name
          "awslogs-region"        = data.aws_region.current.id
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-${var.service_a_config.name}"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

resource "aws_ecs_task_definition" "service_b" {
  family                   = "${var.project_name}-${var.environment}-${var.service_b_config.name}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.service_b_config.cpu
  memory                   = var.service_b_config.memory
  execution_role_arn       = local.task_execution_role_arn
  task_role_arn            = local.task_role_arn

  container_definitions = jsonencode([
    {
      name      = var.service_b_config.name
      image     = var.service_b_config.image != "" ? var.service_b_config.image : "${var.ecr_repository_urls["pertino-service-b"]}:latest"
      essential = true

      portMappings = [
        {
          containerPort = var.service_b_config.port
          protocol      = "tcp"
        }
      ]

      environment = [
        for key, value in var.service_b_config.environment_vars : {
          name  = key
          value = value
        }
      ]

      secrets = length(var.service_b_config.secrets) > 0 ? [
        for env_var_name, secret_arn in var.service_b_config.secrets : {
          name      = env_var_name
          valueFrom = secret_arn
        }
      ] : []

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.service_b.name
          "awslogs-region"        = data.aws_region.current.id
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-${var.service_b_config.name}"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# Get current region
data "aws_region" "current" {}

# ECS Services
resource "aws_ecs_service" "service_a" {
  name                   = "${var.project_name}-${var.environment}-${var.service_a_config.name}"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.service_a.arn
  desired_count          = var.service_a_config.desired_count
  launch_type            = "FARGATE"
  enable_execute_command = true

  # Health check grace period: 태스크 시작 후 health check를 시작하기 전 대기 시간 (초)
  # 애플리케이션 시작에 약 82초 소요되므로 여유있게 120초 설정
  health_check_grace_period_seconds = 120

  # Deployment controller: ECS (rolling) or CODE_DEPLOY (blue/green)
  # NOTE: Changing this requires service recreation
  deployment_controller {
    type = var.enable_blue_green ? "CODE_DEPLOY" : "ECS"
  }

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = false
  }

  # Load balancer configuration
  # For blue/green: CodeDeploy manages target group switching, but we still need initial TG
  dynamic "load_balancer" {
    for_each = var.service_a_target_group_arn != "" ? [1] : []
    content {
      target_group_arn = var.service_a_target_group_arn
      container_name   = var.service_a_config.name
      container_port   = var.service_a_config.port
    }
  }

  service_registries {
    registry_arn = aws_service_discovery_service.service_a.arn
  }

  depends_on = [
    aws_service_discovery_service.service_a
  ]

  tags = merge(
    var.tags,
    {
      Name           = "${var.project_name}-${var.environment}-${var.service_a_config.name}"
      Environment    = var.environment
      Project        = var.project_name
      DeploymentType = var.enable_blue_green ? "blue-green" : "rolling"
    }
  )

  # For CODE_DEPLOY controller, CodeDeploy manages task_definition updates
  # Terraform should ignore changes to avoid conflicts
  lifecycle {
    ignore_changes = [
      task_definition,
      load_balancer,
      desired_count,
    ]
  }
}

resource "aws_ecs_service" "service_b" {
  name                   = "${var.project_name}-${var.environment}-${var.service_b_config.name}"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.service_b.arn
  desired_count          = var.service_b_config.desired_count
  launch_type            = "FARGATE"
  enable_execute_command = true

  # Health check grace period: 태스크 시작 후 health check를 시작하기 전 대기 시간 (초)
  # 애플리케이션 시작 시간에 맞춰 설정 (service-b는 FastAPI이므로 더 빠를 수 있지만 일관성을 위해 동일하게 설정)
  health_check_grace_period_seconds = 120

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = false
  }

  dynamic "load_balancer" {
    for_each = var.service_b_target_group_arn != "" ? [1] : []
    content {
      target_group_arn = var.service_b_target_group_arn
      container_name   = var.service_b_config.name
      container_port   = var.service_b_config.port
    }
  }

  service_registries {
    registry_arn = aws_service_discovery_service.service_b.arn
  }

  depends_on = [
    aws_service_discovery_service.service_b
  ]

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-${var.service_b_config.name}"
      Environment = var.environment
      Project     = var.project_name
    }
  )

  lifecycle {
    ignore_changes = [desired_count]
  }
}

# =============================================================================
# Auto Scaling
# =============================================================================

# --- Service A Auto Scaling ---
resource "aws_appautoscaling_target" "service_a" {
  max_capacity       = var.service_a_autoscaling.max_capacity
  min_capacity       = var.service_a_autoscaling.min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.service_a.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "service_a_requests" {
  count = var.alb_arn_suffix != "" ? 1 : 0

  name               = "${var.project_name}-${var.environment}-service-a-requests"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.service_a.resource_id
  scalable_dimension = aws_appautoscaling_target.service_a.scalable_dimension
  service_namespace  = aws_appautoscaling_target.service_a.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 100

    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${var.alb_arn_suffix}/${var.service_a_target_group_arn_suffix}"
    }

    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_policy" "service_a_cpu" {
  name               = "${var.project_name}-${var.environment}-service-a-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.service_a.resource_id
  scalable_dimension = aws_appautoscaling_target.service_a.scalable_dimension
  service_namespace  = aws_appautoscaling_target.service_a.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# --- Service B Auto Scaling ---
resource "aws_appautoscaling_target" "service_b" {
  max_capacity       = var.service_b_autoscaling.max_capacity
  min_capacity       = var.service_b_autoscaling.min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.service_b.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "service_b_cpu" {
  name               = "${var.project_name}-${var.environment}-service-b-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.service_b.resource_id
  scalable_dimension = aws_appautoscaling_target.service_b.scalable_dimension
  service_namespace  = aws_appautoscaling_target.service_b.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_policy" "service_b_memory" {
  name               = "${var.project_name}-${var.environment}-service-b-memory"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.service_b.resource_id
  scalable_dimension = aws_appautoscaling_target.service_b.scalable_dimension
  service_namespace  = aws_appautoscaling_target.service_b.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }

    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
