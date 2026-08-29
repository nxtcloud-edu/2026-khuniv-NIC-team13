output "alb_id" {
  description = "ID of the Application Load Balancer"
  value       = aws_lb.main.id
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.main.arn
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  value       = aws_lb.main.zone_id
}

output "service_a_target_group_arn" {
  description = "ARN of the Service A target group"
  value       = aws_lb_target_group.service_a.arn
}

output "service_a_target_group_id" {
  description = "ID of the Service A target group"
  value       = aws_lb_target_group.service_a.id
}

output "alb_arn_suffix" {
  description = "ARN suffix of the ALB (for CloudWatch metrics)"
  value       = aws_lb.main.arn_suffix
}

output "service_a_target_group_arn_suffix" {
  description = "ARN suffix of the Service A target group (for CloudWatch metrics)"
  value       = aws_lb_target_group.service_a.arn_suffix
}

# Blue/Green Deployment Outputs
output "service_a_green_target_group_arn" {
  description = "ARN of the Service A green target group (for blue/green deployment)"
  value       = var.enable_blue_green ? aws_lb_target_group.service_a_green[0].arn : ""
}

output "service_a_green_target_group_name" {
  description = "Name of the Service A green target group"
  value       = var.enable_blue_green ? aws_lb_target_group.service_a_green[0].name : ""
}

output "service_a_target_group_name" {
  description = "Name of the Service A (blue) target group"
  value       = aws_lb_target_group.service_a.name
}

output "https_listener_arn" {
  description = "ARN of the HTTPS listener (production traffic)"
  value       = length(aws_lb_listener.https) > 0 ? aws_lb_listener.https[0].arn : ""
}

output "test_listener_arn" {
  description = "ARN of the test listener (green validation traffic)"
  value       = var.enable_blue_green && length(aws_lb_listener.test) > 0 ? aws_lb_listener.test[0].arn : ""
}