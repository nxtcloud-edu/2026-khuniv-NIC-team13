# AWS Secrets Manager for Service B API keys.
# Terraform manages only the secret metadata (name/ARN/tags).
# Actual secret values should be set via AWS Console or CI/CD pipeline.

resource "aws_secretsmanager_secret" "service_b_openai_key" {
  name        = "${var.project_name}-${var.environment}-service-b-openai-key"
  description = "OpenAI API key for Service B"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Service     = "service-b"
  }
}

resource "aws_secretsmanager_secret" "service_b_anthropic_key" {
  name        = "${var.project_name}-${var.environment}-service-b-anthropic-key"
  description = "Anthropic API key for Service B"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Service     = "service-b"
  }
}

resource "aws_secretsmanager_secret" "service_b_deepseek_key" {
  name        = "${var.project_name}-${var.environment}-service-b-deepseek-key"
  description = "DeepSeek API key for Service B"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Service     = "service-b"
  }
}

resource "aws_secretsmanager_secret" "service_b_langsmith_key" {
  name        = "${var.project_name}-${var.environment}-service-b-langsmith-key"
  description = "LangSmith API key for Service B"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Service     = "service-b"
  }
}

resource "aws_secretsmanager_secret" "service_b_elastic_cloud_key" {
  name        = "${var.project_name}-${var.environment}-service-b-elastic-cloud-key"
  description = "Elastic Cloud API key for Service B"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Service     = "service-b"
  }
}

resource "aws_secretsmanager_secret" "service_b_elastic_password" {
  name        = "${var.project_name}-${var.environment}-service-b-elastic-password"
  description = "Elastic password for Service B"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Service     = "service-b"
  }
}

resource "aws_secretsmanager_secret" "service_b_tavily_key" {
  name        = "${var.project_name}-${var.environment}-service-b-tavily-key"
  description = "Tavily API key for Service B"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Service     = "service-b"
  }
}

# Grafana Cloud configuration for Alloy metrics export
resource "aws_secretsmanager_secret" "grafana_cloud_prometheus_endpoint" {
  name        = "${var.project_name}-${var.environment}-grafana-cloud-prometheus-endpoint"
  description = "Grafana Cloud Prometheus remote_write endpoint URL"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Service     = "grafana-alloy"
  }
}

resource "aws_secretsmanager_secret" "grafana_cloud_prometheus_username" {
  name        = "${var.project_name}-${var.environment}-grafana-cloud-prometheus-username"
  description = "Grafana Cloud Prometheus username (instance/tenant ID)"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Service     = "grafana-alloy"
  }
}

resource "aws_secretsmanager_secret" "grafana_cloud_api_key" {
  name        = "${var.project_name}-${var.environment}-grafana-cloud-api-key"
  description = "Grafana Cloud API key for Alloy metrics export"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Service     = "grafana-alloy"
  }
}

# AWS Secrets Manager for Service A
resource "aws_secretsmanager_secret" "service_a_analysis_service_base_url" {
  name        = "${var.project_name}-${var.environment}-service-a-analysis-service-base-url"
  description = "Analysis Service base URL for Service A"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Service     = "service-a"
  }
}
