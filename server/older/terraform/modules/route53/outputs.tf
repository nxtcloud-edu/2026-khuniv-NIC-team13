output "hosted_zone_id" {
  description = "ID of the Route53 Hosted Zone"
  value       = local.hosted_zone_id != "" ? local.hosted_zone_id : null
}

output "hosted_zone_name_servers" {
  description = "Name servers of the Route53 Hosted Zone"
  value       = var.create_hosted_zone && var.domain_name != "" && length(aws_route53_zone.main) > 0 ? aws_route53_zone.main[0].name_servers : (var.existing_hosted_zone_id != "" && length(data.aws_route53_zone.existing) > 0 ? data.aws_route53_zone.existing[0].name_servers : null)
}

output "cloudfront_certificate_arn" {
  description = "ARN of the ACM certificate for CloudFront (us-east-1)"
  value       = local.cloudfront_certificate_arn != "" ? local.cloudfront_certificate_arn : ""
}

output "alb_certificate_arn" {
  description = "ARN of the ACM certificate for ALB (ap-northeast-2)"
  value       = local.alb_certificate_arn != "" ? local.alb_certificate_arn : ""
}

# Backward compatibility - deprecated, use cloudfront_certificate_arn instead
output "certificate_arn" {
  description = "ARN of the ACM certificate (deprecated, use cloudfront_certificate_arn)"
  value       = local.cloudfront_certificate_arn != "" ? local.cloudfront_certificate_arn : ""
}

output "fqdn" {
  description = "Fully qualified domain name"
  value       = var.domain_name != "" && local.hosted_zone_id != "" && length(aws_route53_record.cloudfront) > 0 ? aws_route53_record.cloudfront[0].fqdn : ""
}

output "cloudfront_alias_name" {
  description = "CloudFront distribution domain name"
  value       = data.aws_cloudfront_distribution.main.domain_name
}

