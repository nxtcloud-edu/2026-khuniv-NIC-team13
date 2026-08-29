locals {
  gsi_attr_maps = [
    for gsi in var.global_secondary_indexes : merge(
      { (gsi.hash_key) = gsi.hash_key_type },
      gsi.range_key != "" ? { (gsi.range_key) = gsi.range_key_type } : {}
    )
  ]
  gsi_attrs_flat = length(local.gsi_attr_maps) > 0 ? merge(local.gsi_attr_maps...) : {}
  primary_keys   = compact([var.hash_key, var.range_key != "" ? var.range_key : ""])
  extra_gsi_attrs = {
    for k, v in local.gsi_attrs_flat : k => v
    if !contains(local.primary_keys, k)
  }
}

# DynamoDB Table
resource "aws_dynamodb_table" "main" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = var.hash_key
  range_key    = var.range_key != "" ? var.range_key : null

  attribute {
    name = var.hash_key
    type = var.hash_key_type
  }

  dynamic "attribute" {
    for_each = var.range_key != "" ? [1] : []
    content {
      name = var.range_key
      type = var.range_key_type
    }
  }

  dynamic "attribute" {
    for_each = local.extra_gsi_attrs
    content {
      name = attribute.key
      type = attribute.value
    }
  }

  dynamic "global_secondary_index" {
    for_each = var.global_secondary_indexes
    content {
      name            = global_secondary_index.value.name
      hash_key        = global_secondary_index.value.hash_key
      range_key       = global_secondary_index.value.range_key != "" ? global_secondary_index.value.range_key : null
      projection_type = global_secondary_index.value.projection_type
    }
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  server_side_encryption {
    enabled     = var.enable_encryption
    kms_key_arn = var.enable_encryption && var.kms_key_id != null ? var.kms_key_id : null
  }

  dynamic "ttl" {
    for_each = var.ttl_attribute != null ? [1] : []
    content {
      attribute_name = var.ttl_attribute
      enabled        = true
    }
  }

  tags = merge(
    var.tags,
    {
      Name        = var.table_name
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

