# Route53 Hosted Zone
resource "aws_route53_zone" "main" {
  count = var.create_hosted_zone && var.domain_name != "" ? 1 : 0

  name = var.domain_name

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-${var.domain_name}"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# Get existing Hosted Zone if not creating new one
data "aws_route53_zone" "existing" {
  count   = !var.create_hosted_zone && var.existing_hosted_zone_id != "" ? 1 : 0
  zone_id = var.existing_hosted_zone_id
}

# Local values for Hosted Zone
locals {
  hosted_zone_id   = var.create_hosted_zone && var.domain_name != "" && length(aws_route53_zone.main) > 0 ? aws_route53_zone.main[0].zone_id : (var.existing_hosted_zone_id != "" && length(data.aws_route53_zone.existing) > 0 ? data.aws_route53_zone.existing[0].zone_id : "")
  hosted_zone_name = var.create_hosted_zone && var.domain_name != "" && length(aws_route53_zone.main) > 0 ? aws_route53_zone.main[0].name : (var.existing_hosted_zone_id != "" && length(data.aws_route53_zone.existing) > 0 ? data.aws_route53_zone.existing[0].name : "")
}

# ACM Certificate (us-east-1 for CloudFront)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}
resource "aws_acm_certificate" "cloudfront" {
  count = var.create_acm_certificate && var.domain_name != "" ? 1 : 0

  provider          = aws.us_east_1
  domain_name       = var.domain_name
  validation_method = "DNS"

  subject_alternative_names = []

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-${var.domain_name}-cloudfront"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# ACM Certificate (ap-northeast-2 for ALB)
resource "aws_acm_certificate" "alb" {
  count = var.create_acm_certificate && var.domain_name != "" ? 1 : 0

  domain_name       = var.domain_name
  validation_method = "DNS"

  subject_alternative_names = []

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-${var.domain_name}-alb"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# ACM Certificate Validation Records (CloudFront)
resource "aws_route53_record" "cloudfront_cert_validation" {
  for_each = var.create_acm_certificate && var.domain_name != "" && length(aws_acm_certificate.cloudfront) > 0 ? {
    for dvo in aws_acm_certificate.cloudfront[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = local.hosted_zone_id
}

# ACM Certificate Validation Records (ALB)
resource "aws_route53_record" "alb_cert_validation" {
  for_each = var.create_acm_certificate && var.domain_name != "" && length(aws_acm_certificate.alb) > 0 ? {
    for dvo in aws_acm_certificate.alb[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = local.hosted_zone_id
}

# ACM Certificate Validation (CloudFront)
resource "aws_acm_certificate_validation" "cloudfront" {
  count = var.create_acm_certificate && var.domain_name != "" ? 1 : 0

  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.cloudfront[0].arn
  validation_record_fqdns = [for record in aws_route53_record.cloudfront_cert_validation : record.fqdn]
}

# ACM Certificate Validation (ALB)
resource "aws_acm_certificate_validation" "alb" {
  count = var.create_acm_certificate && var.domain_name != "" ? 1 : 0

  certificate_arn         = aws_acm_certificate.alb[0].arn
  validation_record_fqdns = [for record in aws_route53_record.alb_cert_validation : record.fqdn]
}

# Local values for certificate ARNs
locals {
  cloudfront_certificate_arn = var.create_acm_certificate && var.domain_name != "" && length(aws_acm_certificate_validation.cloudfront) > 0 ? aws_acm_certificate_validation.cloudfront[0].certificate_arn : (var.acm_certificate_arn != "" ? var.acm_certificate_arn : "")
  alb_certificate_arn        = var.create_acm_certificate && var.domain_name != "" && length(aws_acm_certificate_validation.alb) > 0 ? aws_acm_certificate_validation.alb[0].certificate_arn : ""
}

# Get CloudFront Distribution
data "aws_cloudfront_distribution" "main" {
  id = var.cloudfront_distribution_id
}

# Route53 A Record (Alias to CloudFront)
resource "aws_route53_record" "cloudfront" {
  count = var.domain_name != "" && local.hosted_zone_id != "" ? 1 : 0

  zone_id = local.hosted_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = data.aws_cloudfront_distribution.main.domain_name
    zone_id                = data.aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}

# Route53 AAAA Record (IPv6 Alias to CloudFront)
resource "aws_route53_record" "cloudfront_ipv6" {
  count = var.domain_name != "" && local.hosted_zone_id != "" ? 1 : 0

  zone_id = local.hosted_zone_id
  name    = var.domain_name
  type    = "AAAA"

  alias {
    name                   = data.aws_cloudfront_distribution.main.domain_name
    zone_id                = data.aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}

