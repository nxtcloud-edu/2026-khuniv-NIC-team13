output "service_name" {
  description = "Name of the Grafana Alloy ECS service"
  value       = aws_ecs_service.alloy.name
}

output "task_definition_arn" {
  description = "ARN of the Grafana Alloy task definition"
  value       = aws_ecs_task_definition.alloy.arn
}

output "log_group_name" {
  description = "CloudWatch Log Group name for Grafana Alloy"
  value       = aws_cloudwatch_log_group.alloy.name
}
