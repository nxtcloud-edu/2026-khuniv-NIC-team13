output "repository_urls" {
  description = "Map of repository URLs"
  value       = { for k, v in aws_ecr_repository.main : k => v.repository_url }
}

output "repository_arns" {
  description = "Map of repository ARNs"
  value       = { for k, v in aws_ecr_repository.main : k => v.arn }
}

output "repository_names" {
  description = "List of repository names"
  value       = [for v in aws_ecr_repository.main : v.name]
}

output "repository_registry_id" {
  description = "Registry ID where the repositories were created"
  value       = length(aws_ecr_repository.main) > 0 ? aws_ecr_repository.main[keys(aws_ecr_repository.main)[0]].registry_id : null
}

