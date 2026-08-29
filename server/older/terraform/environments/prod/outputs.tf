# =============================================================================
# Terraform Outputs for Prod Environment
# =============================================================================

# -----------------------------------------------------------------------------
# VPC Outputs
# -----------------------------------------------------------------------------
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

# -----------------------------------------------------------------------------
# Route53 & HTTPS Outputs
# -----------------------------------------------------------------------------
output "route53_hosted_zone_id" {
  description = "Route53 Hosted Zone ID"
  value       = module.route53.hosted_zone_id
}

output "route53_name_servers" {
  description = "Route53 Hosted Zone name servers (update your domain registrar with these)"
  value       = module.route53.hosted_zone_name_servers
}

output "cloudfront_certificate_arn" {
  description = "ACM certificate ARN for CloudFront (us-east-1)"
  value       = module.route53.cloudfront_certificate_arn
}

output "alb_certificate_arn" {
  description = "ACM certificate ARN for ALB (ap-northeast-2)"
  value       = module.route53.alb_certificate_arn
}

output "domain_fqdn" {
  description = "Fully qualified domain name (HTTPS endpoint)"
  value       = module.route53.fqdn
}

# -----------------------------------------------------------------------------
# CloudFront Outputs
# -----------------------------------------------------------------------------
output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = module.cloudfront.distribution_id
}

output "cloudfront_distribution_domain" {
  description = "CloudFront distribution domain name"
  value       = module.cloudfront.domain_name
}

# -----------------------------------------------------------------------------
# ALB Outputs
# -----------------------------------------------------------------------------
output "alb_dns_name" {
  description = "ALB DNS name"
  value       = module.alb.alb_dns_name
}

# -----------------------------------------------------------------------------
# ECS Outputs
# -----------------------------------------------------------------------------
output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "service_discovery_namespace" {
  description = "Service Discovery namespace (internal DNS)"
  value       = "${var.project_name}.local"
}

# -----------------------------------------------------------------------------
# Access URLs
# -----------------------------------------------------------------------------
output "https_endpoint" {
  description = "HTTPS endpoint URL (requires domain_name to be set)"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "Set domain_name variable to enable HTTPS"
}

output "cloudfront_endpoint" {
  description = "CloudFront endpoint URL (always available)"
  value       = "https://${module.cloudfront.domain_name}"
}

# -----------------------------------------------------------------------------
# Blue/Green Deployment Outputs
# -----------------------------------------------------------------------------
output "codedeploy_app_name" {
  description = "CodeDeploy application name for Service A"
  value       = module.ecs.codedeploy_app_name
}

output "codedeploy_deployment_group_name" {
  description = "CodeDeploy deployment group name for Service A"
  value       = module.ecs.codedeploy_deployment_group_name
}

output "test_listener_endpoint" {
  description = "Test listener endpoint for green environment validation"
  value       = var.domain_name != "" ? "https://${var.domain_name}:8443" : "https://${module.alb.alb_dns_name}:8443"
}

output "service_a_task_definition_family" {
  description = "Task definition family for Service A (used in AppSpec)"
  value       = module.ecs.service_a_task_definition_family
}

# -----------------------------------------------------------------------------
# Grafana Alloy Outputs
# -----------------------------------------------------------------------------
output "grafana_alloy_service_name" {
  description = "Grafana Alloy ECS service name"
  value       = module.grafana_alloy.service_name
}

output "grafana_alloy_log_group" {
  description = "CloudWatch Log Group for Grafana Alloy"
  value       = module.grafana_alloy.log_group_name
}
