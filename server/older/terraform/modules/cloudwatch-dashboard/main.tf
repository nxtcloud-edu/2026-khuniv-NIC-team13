# CloudWatch Dashboard Module - Main

locals {
  dashboard_name = "${var.dashboard_name}-${var.environment}"
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = local.dashboard_name

  dashboard_body = jsonencode({
    widgets = concat(
      # ===========================================
      # Section 1: ECS Overview
      # ===========================================
      [
        # Header: ECS Overview
        {
          type   = "text"
          x      = 0
          y      = 0
          width  = 24
          height = 1
          properties = {
            markdown = "# ECS Services Overview"
          }
        },
        # Service A - CPU Utilization
        {
          type   = "metric"
          x      = 0
          y      = 1
          width  = 6
          height = 6
          properties = {
            title  = "Service A - CPU Utilization"
            region = var.region
            metrics = [
              ["ECS/ContainerInsights", "CpuUtilized", "ClusterName", var.cluster_name, "ServiceName", "${var.project_name}-${var.environment}-${var.service_a_name}", { label = "CPU Used" }],
              [".", "CpuReserved", ".", ".", ".", ".", { label = "CPU Reserved" }]
            ]
            period  = 60
            stat    = "Average"
            view    = "timeSeries"
            stacked = false
          }
        },
        # Service A - Memory Utilization
        {
          type   = "metric"
          x      = 6
          y      = 1
          width  = 6
          height = 6
          properties = {
            title  = "Service A - Memory Utilization"
            region = var.region
            metrics = [
              ["ECS/ContainerInsights", "MemoryUtilized", "ClusterName", var.cluster_name, "ServiceName", "${var.project_name}-${var.environment}-${var.service_a_name}", { label = "Memory Used (MB)" }],
              [".", "MemoryReserved", ".", ".", ".", ".", { label = "Memory Reserved (MB)" }]
            ]
            period  = 60
            stat    = "Average"
            view    = "timeSeries"
            stacked = false
          }
        },
        # Service B - CPU Utilization
        {
          type   = "metric"
          x      = 12
          y      = 1
          width  = 6
          height = 6
          properties = {
            title  = "Service B - CPU Utilization"
            region = var.region
            metrics = [
              ["ECS/ContainerInsights", "CpuUtilized", "ClusterName", var.cluster_name, "ServiceName", "${var.project_name}-${var.environment}-${var.service_b_name}", { label = "CPU Used" }],
              [".", "CpuReserved", ".", ".", ".", ".", { label = "CPU Reserved" }]
            ]
            period  = 60
            stat    = "Average"
            view    = "timeSeries"
            stacked = false
          }
        },
        # Service B - Memory Utilization
        {
          type   = "metric"
          x      = 18
          y      = 1
          width  = 6
          height = 6
          properties = {
            title  = "Service B - Memory Utilization"
            region = var.region
            metrics = [
              ["ECS/ContainerInsights", "MemoryUtilized", "ClusterName", var.cluster_name, "ServiceName", "${var.project_name}-${var.environment}-${var.service_b_name}", { label = "Memory Used (MB)" }],
              [".", "MemoryReserved", ".", ".", ".", ".", { label = "Memory Reserved (MB)" }]
            ]
            period  = 60
            stat    = "Average"
            view    = "timeSeries"
            stacked = false
          }
        },
        # ECS Task Count - Both Services
        {
          type   = "metric"
          x      = 0
          y      = 7
          width  = 8
          height = 6
          properties = {
            title  = "ECS Task Count"
            region = var.region
            metrics = [
              ["ECS/ContainerInsights", "RunningTaskCount", "ClusterName", var.cluster_name, "ServiceName", "${var.project_name}-${var.environment}-${var.service_a_name}", { label = "Service A Running" }],
              [".", "DesiredTaskCount", ".", ".", ".", ".", { label = "Service A Desired" }],
              [".", "RunningTaskCount", ".", ".", "ServiceName", "${var.project_name}-${var.environment}-${var.service_b_name}", { label = "Service B Running" }],
              [".", "DesiredTaskCount", ".", ".", ".", ".", { label = "Service B Desired" }]
            ]
            period  = 60
            stat    = "Average"
            view    = "timeSeries"
            stacked = false
          }
        },
        # ECS Network - Service A
        {
          type   = "metric"
          x      = 8
          y      = 7
          width  = 8
          height = 6
          properties = {
            title  = "Service A - Network I/O"
            region = var.region
            metrics = [
              ["ECS/ContainerInsights", "NetworkRxBytes", "ClusterName", var.cluster_name, "ServiceName", "${var.project_name}-${var.environment}-${var.service_a_name}", { label = "RX Bytes" }],
              [".", "NetworkTxBytes", ".", ".", ".", ".", { label = "TX Bytes" }]
            ]
            period  = 60
            stat    = "Average"
            view    = "timeSeries"
            stacked = false
          }
        },
        # ECS Network - Service B
        {
          type   = "metric"
          x      = 16
          y      = 7
          width  = 8
          height = 6
          properties = {
            title  = "Service B - Network I/O"
            region = var.region
            metrics = [
              ["ECS/ContainerInsights", "NetworkRxBytes", "ClusterName", var.cluster_name, "ServiceName", "${var.project_name}-${var.environment}-${var.service_b_name}", { label = "RX Bytes" }],
              [".", "NetworkTxBytes", ".", ".", ".", ".", { label = "TX Bytes" }]
            ]
            period  = 60
            stat    = "Average"
            view    = "timeSeries"
            stacked = false
          }
        }
      ],
      # ===========================================
      # Section 2: ALB Metrics
      # ===========================================
      [
        # Header: ALB Metrics
        {
          type   = "text"
          x      = 0
          y      = 13
          width  = 24
          height = 1
          properties = {
            markdown = "# Application Load Balancer Metrics"
          }
        },
        # ALB Request Count
        {
          type   = "metric"
          x      = 0
          y      = 14
          width  = 8
          height = 6
          properties = {
            title  = "ALB Request Count"
            region = var.region
            metrics = [
              ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", var.alb_arn_suffix, { stat = "Sum", label = "Total Requests" }]
            ]
            period  = 60
            view    = "timeSeries"
            stacked = false
          }
        },
        # ALB Target Response Time
        {
          type   = "metric"
          x      = 8
          y      = 14
          width  = 8
          height = 6
          properties = {
            title  = "Target Response Time"
            region = var.region
            metrics = [
              ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", var.alb_arn_suffix, { stat = "Average", label = "Average" }],
              ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", var.alb_arn_suffix, { stat = "p99", label = "p99" }],
              ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", var.alb_arn_suffix, { stat = "p95", label = "p95" }]
            ]
            period  = 60
            view    = "timeSeries"
            stacked = false
            yAxis = {
              left = {
                min = 0
              }
            }
          }
        },
        # ALB Active Connections
        {
          type   = "metric"
          x      = 16
          y      = 14
          width  = 8
          height = 6
          properties = {
            title  = "Active Connections"
            region = var.region
            metrics = [
              ["AWS/ApplicationELB", "ActiveConnectionCount", "LoadBalancer", var.alb_arn_suffix, { stat = "Sum", label = "Active Connections" }],
              [".", "NewConnectionCount", ".", ".", { stat = "Sum", label = "New Connections" }]
            ]
            period  = 60
            view    = "timeSeries"
            stacked = false
          }
        },
        # ALB HTTP Status Codes
        {
          type   = "metric"
          x      = 0
          y      = 20
          width  = 12
          height = 6
          properties = {
            title  = "HTTP Status Codes"
            region = var.region
            metrics = [
              ["AWS/ApplicationELB", "HTTPCode_Target_2XX_Count", "LoadBalancer", var.alb_arn_suffix, { stat = "Sum", label = "2XX (Success)", color = "#2ca02c" }],
              [".", "HTTPCode_Target_4XX_Count", ".", ".", { stat = "Sum", label = "4XX (Client Error)", color = "#ff7f0e" }],
              [".", "HTTPCode_Target_5XX_Count", ".", ".", { stat = "Sum", label = "5XX (Server Error)", color = "#d62728" }],
              [".", "HTTPCode_ELB_5XX_Count", ".", ".", { stat = "Sum", label = "ELB 5XX", color = "#9467bd" }]
            ]
            period  = 60
            view    = "timeSeries"
            stacked = false
          }
        },
        # Target Group Health
        {
          type   = "metric"
          x      = 12
          y      = 20
          width  = 12
          height = 6
          properties = {
            title  = "Target Group Health (Service A)"
            region = var.region
            metrics = [
              ["AWS/ApplicationELB", "HealthyHostCount", "TargetGroup", var.target_group_arn_suffix, "LoadBalancer", var.alb_arn_suffix, { stat = "Average", label = "Healthy Hosts", color = "#2ca02c" }],
              [".", "UnHealthyHostCount", ".", ".", ".", ".", { stat = "Average", label = "Unhealthy Hosts", color = "#d62728" }]
            ]
            period  = 60
            view    = "timeSeries"
            stacked = false
          }
        },
        # Error Rate Percentage
        {
          type   = "metric"
          x      = 0
          y      = 26
          width  = 12
          height = 6
          properties = {
            title  = "Error Rate (%)"
            region = var.region
            metrics = [
              [{
                expression = "(m1+m2)/m3*100"
                label      = "Error Rate %"
                id         = "e1"
                color      = "#d62728"
              }],
              ["AWS/ApplicationELB", "HTTPCode_Target_4XX_Count", "LoadBalancer", var.alb_arn_suffix, { id = "m1", visible = false, stat = "Sum" }],
              [".", "HTTPCode_Target_5XX_Count", ".", ".", { id = "m2", visible = false, stat = "Sum" }],
              [".", "RequestCount", ".", ".", { id = "m3", visible = false, stat = "Sum" }]
            ]
            period  = 300
            view    = "timeSeries"
            stacked = false
            yAxis = {
              left = {
                min = 0
                max = 100
              }
            }
          }
        },
        # Rejected Connections
        {
          type   = "metric"
          x      = 12
          y      = 26
          width  = 12
          height = 6
          properties = {
            title  = "Rejected & Processed Bytes"
            region = var.region
            metrics = [
              ["AWS/ApplicationELB", "RejectedConnectionCount", "LoadBalancer", var.alb_arn_suffix, { stat = "Sum", label = "Rejected Connections" }],
              [".", "ProcessedBytes", ".", ".", { stat = "Sum", label = "Processed Bytes" }]
            ]
            period  = 60
            view    = "timeSeries"
            stacked = false
          }
        }
      ],
      # ===========================================
      # Section 3: DynamoDB Metrics
      # ===========================================
      [
        # Header: DynamoDB Metrics
        {
          type   = "text"
          x      = 0
          y      = 32
          width  = 24
          height = 1
          properties = {
            markdown = "# DynamoDB Tables Metrics"
          }
        },
        # DynamoDB - Consumed Capacity (Read)
        {
          type   = "metric"
          x      = 0
          y      = 33
          width  = 12
          height = 6
          properties = {
            title  = "DynamoDB - Read Capacity (All Tables)"
            region = var.region
            metrics = [
              for table_name in var.dynamodb_table_names :
                ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", table_name, { stat = "Sum", label = table_name }]
            ]
            period  = 60
            view    = "timeSeries"
            stacked = true
          }
        },
        # DynamoDB - Consumed Capacity (Write)
        {
          type   = "metric"
          x      = 12
          y      = 33
          width  = 12
          height = 6
          properties = {
            title  = "DynamoDB - Write Capacity (All Tables)"
            region = var.region
            metrics = [
              for table_name in var.dynamodb_table_names :
                ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", table_name, { stat = "Sum", label = table_name }]
            ]
            period  = 60
            view    = "timeSeries"
            stacked = true
          }
        },
        # DynamoDB - Throttled Requests
        {
          type   = "metric"
          x      = 0
          y      = 39
          width  = 12
          height = 6
          properties = {
            title  = "DynamoDB - Throttled Requests"
            region = var.region
            metrics = concat([
              for table_name in var.dynamodb_table_names : [
                ["AWS/DynamoDB", "ReadThrottledRequests", "TableName", table_name, { stat = "Sum", label = "${table_name} (Read)" }],
                [".", "WriteThrottledRequests", ".", ".", { stat = "Sum", label = "${table_name} (Write)" }]
              ]
            ]...)
            period  = 60
            view    = "timeSeries"
            stacked = false
          }
        },
        # DynamoDB - Errors
        {
          type   = "metric"
          x      = 12
          y      = 39
          width  = 12
          height = 6
          properties = {
            title  = "DynamoDB - User & System Errors"
            region = var.region
            metrics = concat([
              for table_name in var.dynamodb_table_names : [
                ["AWS/DynamoDB", "UserErrors", "TableName", table_name, { stat = "Sum", label = "${table_name} (User)" }],
                [".", "SystemErrors", ".", ".", { stat = "Sum", label = "${table_name} (System)" }]
              ]
            ]...)
            period  = 60
            view    = "timeSeries"
            stacked = false
          }
        },
        # DynamoDB - Latency
        {
          type   = "metric"
          x      = 0
          y      = 45
          width  = 24
          height = 6
          properties = {
            title  = "DynamoDB - Successful Request Latency (ms)"
            region = var.region
            metrics = concat([
              for table_name in var.dynamodb_table_names : [
                ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table_name, "Operation", "GetItem", { stat = "Average", label = "${table_name} (GetItem)" }],
                [".", ".", ".", ".", "Operation", "PutItem", { stat = "Average", label = "${table_name} (PutItem)" }],
                [".", ".", ".", ".", "Operation", "Query", { stat = "Average", label = "${table_name} (Query)" }]
              ]
            ]...)
            period  = 60
            view    = "timeSeries"
            stacked = false
          }
        }
      ],
      # ===========================================
      # Section 4: CloudWatch Logs
      # ===========================================
      [
        # Header: CloudWatch Logs
        {
          type   = "text"
          x      = 0
          y      = 51
          width  = 24
          height = 1
          properties = {
            markdown = "# Application Logs"
          }
        },
        # Service A - Recent Logs
        {
          type   = "log"
          x      = 0
          y      = 52
          width  = 12
          height = 8
          properties = {
            title  = "Service A - Recent Logs (50)"
            region = var.region
            query  = "SOURCE '${var.service_a_log_group}' | fields @timestamp, @message | sort @timestamp desc | limit 50"
            view   = "table"
          }
        },
        # Service B - Recent Logs
        {
          type   = "log"
          x      = 12
          y      = 52
          width  = 12
          height = 8
          properties = {
            title  = "Service B - Recent Logs (50)"
            region = var.region
            query  = "SOURCE '${var.service_b_log_group}' | fields @timestamp, @message | sort @timestamp desc | limit 50"
            view   = "table"
          }
        },
        # Service A - Error Logs
        {
          type   = "log"
          x      = 0
          y      = 60
          width  = 12
          height = 8
          properties = {
            title  = "Service A - Error Logs"
            region = var.region
            query  = "SOURCE '${var.service_a_log_group}' | fields @timestamp, @message | filter @message like /ERROR|Exception|error|exception/ | sort @timestamp desc | limit 50"
            view   = "table"
          }
        },
        # Service B - Error Logs
        {
          type   = "log"
          x      = 12
          y      = 60
          width  = 12
          height = 8
          properties = {
            title  = "Service B - Error Logs"
            region = var.region
            query  = "SOURCE '${var.service_b_log_group}' | fields @timestamp, @message | filter @message like /ERROR|Exception|error|exception/ | sort @timestamp desc | limit 50"
            view   = "table"
          }
        },
        # Log Error Count Over Time
        {
          type   = "log"
          x      = 0
          y      = 68
          width  = 24
          height = 6
          properties = {
            title   = "Error Log Count Over Time"
            region  = var.region
            query   = "SOURCE '${var.service_a_log_group}' | SOURCE '${var.service_b_log_group}' | filter @message like /ERROR|Exception/ | stats count(*) as error_count by bin(5m)"
            view    = "timeSeries"
            stacked = false
          }
        }
      ]
    )
  })
}
