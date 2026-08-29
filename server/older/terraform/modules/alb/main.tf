# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.project_name}-${var.environment}-${var.name}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.security_group_id]
  subnets            = var.subnet_ids

  enable_deletion_protection = var.enable_deletion_protection
  idle_timeout               = var.idle_timeout

  enable_http2                     = true
  enable_cross_zone_load_balancing = true

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-${var.name}"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# Target Group for Service A
resource "aws_lb_target_group" "service_a" {
  name        = "${var.project_name}-${var.environment}-service-a-tg"
  port        = var.service_a_target_group_config.port
  protocol    = var.service_a_target_group_config.protocol
  vpc_id      = data.aws_subnet.main.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = var.service_a_target_group_config.healthy_threshold
    unhealthy_threshold = var.service_a_target_group_config.unhealthy_threshold
    timeout             = var.service_a_target_group_config.timeout
    interval            = var.service_a_target_group_config.interval
    path                = var.service_a_target_group_config.health_check_path
    port                = var.service_a_target_group_config.health_check_port
    protocol            = var.service_a_target_group_config.health_check_protocol
    matcher             = var.service_a_target_group_config.matcher
  }

  deregistration_delay = 30

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-service-a-tg"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# Get VPC ID from subnet
data "aws_subnet" "main" {
  id = var.subnet_ids[0]
}

# Green Target Group for Blue/Green Deployment
resource "aws_lb_target_group" "service_a_green" {
  count = var.enable_blue_green ? 1 : 0

  name        = "${var.project_name}-${var.environment}-service-a-green-tg"
  port        = var.service_a_target_group_config.port
  protocol    = var.service_a_target_group_config.protocol
  vpc_id      = data.aws_subnet.main.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = var.service_a_target_group_config.healthy_threshold
    unhealthy_threshold = var.service_a_target_group_config.unhealthy_threshold
    timeout             = var.service_a_target_group_config.timeout
    interval            = var.service_a_target_group_config.interval
    path                = var.service_a_target_group_config.health_check_path
    port                = var.service_a_target_group_config.health_check_port
    protocol            = var.service_a_target_group_config.health_check_protocol
    matcher             = var.service_a_target_group_config.matcher
  }

  deregistration_delay = 30

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-service-a-green-tg"
      Environment = var.environment
      Project     = var.project_name
      DeploymentRole = "green"
    }
  )
}

# HTTPS Listener
resource "aws_lb_listener" "https" {
  count = var.certificate_arn != "" ? 1 : 0

  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-Res-PQ-2025-09"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.service_a.arn
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-${var.name}-https-listener"
      Environment = var.environment
      Project     = var.project_name
    }
  )

  # CodeDeploy가 트래픽 시프트 시 default_action을 변경하므로 무시
  lifecycle {
    ignore_changes = [default_action]
  }
}

# Listener Rule for Service A
resource "aws_lb_listener_rule" "service_a" {
  count = var.certificate_arn != "" ? 1 : 0

  listener_arn = aws_lb_listener.https[0].arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.service_a.arn
  }

  condition {
    path_pattern {
      values = ["/api/service-a/*"]
    }
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-service-a-rule"
      Environment = var.environment
      Project     = var.project_name
    }
  )

  # CodeDeploy가 트래픽 시프트 시 action(forward 대상 TG)을 변경하므로 무시
  lifecycle {
    ignore_changes = [action]
  }
}

# Test Traffic Listener for Blue/Green Deployment (Green validation)
resource "aws_lb_listener" "test" {
  count = var.enable_blue_green && var.certificate_arn != "" ? 1 : 0

  load_balancer_arn = aws_lb.main.arn
  port              = var.test_listener_port
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-Res-PQ-2025-09"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.service_a_green[0].arn
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-${var.name}-test-listener"
      Environment = var.environment
      Project     = var.project_name
      Purpose     = "blue-green-test-traffic"
    }
  )

  # CodeDeploy가 배포/시프트 시 default_action을 Blue↔Green TG로 변경하므로 무시
  lifecycle {
    ignore_changes = [default_action]
  }
}

# HTTP Listener
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = var.certificate_arn != "" && var.enable_http_redirect ? "redirect" : "forward"

    dynamic "redirect" {
      for_each = var.certificate_arn != "" && var.enable_http_redirect ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }

    dynamic "forward" {
      for_each = var.certificate_arn == "" || !var.enable_http_redirect ? [1] : []
      content {
        target_group {
          arn = aws_lb_target_group.service_a.arn
        }
      }
    }
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-${var.name}-http-listener"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

