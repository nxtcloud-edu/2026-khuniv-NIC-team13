# Grafana Alloy Module
# Deploys Grafana Alloy as an ECS Fargate service to scrape Prometheus metrics
# from application services and forward them to Grafana Cloud.

data "aws_region" "current" {}

locals {
  alloy_config = templatefile("${path.module}/config.alloy.tpl", {
    scrape_targets = var.scrape_targets
  })
}

# CloudWatch Log Group for Alloy (minimal logging only)
resource "aws_cloudwatch_log_group" "alloy" {
  name              = "/ecs/${var.project_name}-cluster/grafana-alloy"
  retention_in_days = 7

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-grafana-alloy-logs"
    Environment = var.environment
    Project     = var.project_name
  })
}

# IAM Role for Alloy Task Execution (pull image, write logs, read secrets)
resource "aws_iam_role" "alloy_task_execution" {
  name = "${var.project_name}-${var.environment}-alloy-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-alloy-task-execution-role"
    Environment = var.environment
    Project     = var.project_name
  })
}

resource "aws_iam_role_policy_attachment" "alloy_task_execution_managed" {
  role       = aws_iam_role.alloy_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "alloy_task_execution" {
  name = "${var.project_name}-${var.environment}-alloy-task-execution-policy"
  role = aws_iam_role.alloy_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.alloy.arn}:*"
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = values(var.grafana_cloud_secret_arns)
      }
    ]
  })
}

# IAM Role for Alloy Task (runtime — no special permissions needed)
resource "aws_iam_role" "alloy_task" {
  name = "${var.project_name}-${var.environment}-alloy-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-alloy-task-role"
    Environment = var.environment
    Project     = var.project_name
  })
}

# ECS Task Definition
resource "aws_ecs_task_definition" "alloy" {
  family                   = "${var.project_name}-${var.environment}-grafana-alloy"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.alloy_task_execution.arn
  task_role_arn            = aws_iam_role.alloy_task.arn

  container_definitions = jsonencode([{
    name      = "grafana-alloy"
    image     = var.alloy_image
    essential = true

    # grafana/alloy image sets ENTRYPOINT to /bin/alloy.
    # In ECS, "command" becomes CMD and is passed as args to ENTRYPOINT.
    # We want a shell wrapper to materialize config, then exec alloy.
    entryPoint = ["/bin/sh", "-c"]
    command = [
      "echo $ALLOY_CONFIG | base64 -d > /etc/alloy/config.alloy && exec /bin/alloy run /etc/alloy/config.alloy --server.http.listen-addr=0.0.0.0:12345 --stability.level=generally-available"
    ]

    portMappings = [
      { containerPort = 12345, protocol = "tcp" }
    ]

    environment = [
      {
        name  = "ALLOY_CONFIG"
        value = base64encode(local.alloy_config)
      }
    ]

    secrets = [
      {
        name      = "GRAFANA_CLOUD_PROMETHEUS_ENDPOINT"
        valueFrom = var.grafana_cloud_secret_arns.prometheus_endpoint
      },
      {
        name      = "GRAFANA_CLOUD_PROMETHEUS_USERNAME"
        valueFrom = var.grafana_cloud_secret_arns.prometheus_username
      },
      {
        name      = "GRAFANA_CLOUD_API_KEY"
        valueFrom = var.grafana_cloud_secret_arns.api_key
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.alloy.name
        "awslogs-region"        = data.aws_region.current.id
        "awslogs-stream-prefix" = "alloy"
      }
    }
  }])

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-grafana-alloy"
    Environment = var.environment
    Project     = var.project_name
  })
}

# ECS Service
resource "aws_ecs_service" "alloy" {
  name            = "${var.project_name}-${var.environment}-grafana-alloy"
  cluster         = var.cluster_id
  task_definition = aws_ecs_task_definition.alloy.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = false
  }

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-grafana-alloy"
    Environment = var.environment
    Project     = var.project_name
  })
}
