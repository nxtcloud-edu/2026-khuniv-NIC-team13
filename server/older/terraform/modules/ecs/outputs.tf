output "cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.main.id
}

output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "service_a_name" {
  description = "Name of Service A"
  value       = aws_ecs_service.service_a.name
}

output "service_b_name" {
  description = "Name of Service B"
  value       = aws_ecs_service.service_b.name
}

output "service_a_service_discovery_name" {
  description = "Service Discovery DNS name for Service A"
  value       = "${var.service_a_config.name}.${aws_service_discovery_private_dns_namespace.main.name}"
}

output "service_b_service_discovery_name" {
  description = "Service Discovery DNS name for Service B"
  value       = "${var.service_b_config.name}.${aws_service_discovery_private_dns_namespace.main.name}"
}

output "service_discovery_namespace_id" {
  description = "Service Discovery namespace ID"
  value       = aws_service_discovery_private_dns_namespace.main.id
}

output "task_execution_role_arn" {
  description = "ARN of the Task Execution Role"
  value       = local.task_execution_role_arn
}

output "task_role_arn" {
  description = "ARN of the Task Role"
  value       = local.task_role_arn
}

output "service_a_log_group_name" {
  description = "CloudWatch Log Group name for Service A"
  value       = aws_cloudwatch_log_group.service_a.name
}

output "service_b_log_group_name" {
  description = "CloudWatch Log Group name for Service B"
  value       = aws_cloudwatch_log_group.service_b.name
}

# Blue/Green Deployment Outputs
output "codedeploy_app_name" {
  description = "CodeDeploy application name for Service A"
  value       = var.enable_blue_green ? aws_codedeploy_app.service_a[0].name : ""
}

output "codedeploy_deployment_group_name" {
  description = "CodeDeploy deployment group name for Service A"
  value       = var.enable_blue_green ? aws_codedeploy_deployment_group.service_a[0].deployment_group_name : ""
}

output "codedeploy_role_arn" {
  description = "CodeDeploy IAM role ARN"
  value       = var.enable_blue_green ? aws_iam_role.codedeploy[0].arn : ""
}

output "service_a_task_definition_arn" {
  description = "Task definition ARN for Service A (used in AppSpec)"
  value       = aws_ecs_task_definition.service_a.arn
}

output "service_a_task_definition_family" {
  description = "Task definition family for Service A"
  value       = aws_ecs_task_definition.service_a.family
}