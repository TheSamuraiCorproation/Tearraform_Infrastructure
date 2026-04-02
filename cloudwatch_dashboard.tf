resource "aws_cloudwatch_dashboard" "ec2_dashboard" {
  dashboard_name = "EC2-GoldenAMI-Dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 3
        properties = {
          markdown = <<-MD
          # EC2 Lab Monitoring
          This dashboard auto-discovers every EC2 that publishes CloudWatch Agent metrics in the `EC2/LabMonitoring` namespace.

          Metrics are grouped by `InstanceId`, so new VMs appear here automatically once the agent is installed.
          MD
        }
      },

      {
        type   = "metric"
        x      = 0
        y      = 3
        width  = 12
        height = 6
        properties = {
          title      = "CPU Usage (all EC2s)"
          region     = var.aws_region
          period     = 60
          stat       = "Average"
          view       = "timeSeries"
          stacked    = false
          liveData    = true
          metrics = [
            [
              {
                expression = "SEARCH('{EC2/LabMonitoring,InstanceId} MetricName=\"cpu_usage_user\"', 'Average', 60)"
                id         = "cpu_user"
                label      = "cpu_usage_user"
              }
            ],
            [
              {
                expression = "SEARCH('{EC2/LabMonitoring,InstanceId} MetricName=\"cpu_usage_system\"', 'Average', 60)"
                id         = "cpu_system"
                label      = "cpu_usage_system"
              }
            ],
            [
              {
                expression = "SEARCH('{EC2/LabMonitoring,InstanceId} MetricName=\"cpu_usage_idle\"', 'Average', 60)"
                id         = "cpu_idle"
                label      = "cpu_usage_idle"
              }
            ]
          ]
        }
      },

      {
        type   = "metric"
        x      = 12
        y      = 3
        width  = 12
        height = 6
        properties = {
          title      = "Memory Usage (all EC2s)"
          region     = var.aws_region
          period     = 60
          stat       = "Average"
          view       = "timeSeries"
          stacked    = false
          liveData    = true
          metrics = [
            [
              {
                expression = "SEARCH('{EC2/LabMonitoring,InstanceId} MetricName=\"mem_used_percent\"', 'Average', 60)"
                id         = "mem_used"
                label      = "mem_used_percent"
              }
            ]
          ]
        }
      },

      {
        type   = "metric"
        x      = 0
        y      = 9
        width  = 12
        height = 6
        properties = {
          title      = "Disk Usage (all EC2s)"
          region     = var.aws_region
          period     = 60
          stat       = "Average"
          view       = "timeSeries"
          stacked    = false
          liveData    = true
          metrics = [
            [
              {
                expression = "SEARCH('{EC2/LabMonitoring,InstanceId} MetricName=\"used_percent\"', 'Average', 60)"
                id         = "disk_used"
                label      = "used_percent"
              }
            ]
          ]
        }
      },

      {
        type   = "metric"
        x      = 12
        y      = 9
        width  = 12
        height = 6
        properties = {
          title      = "Network Traffic (all EC2s)"
          region     = var.aws_region
          period     = 60
          stat       = "Sum"
          view       = "timeSeries"
          stacked    = false
          liveData    = true
          metrics = [
            [
              {
                expression = "SEARCH('{EC2/LabMonitoring,InstanceId} MetricName=\"bytes_recv\"', 'Sum', 60)"
                id         = "net_recv"
                label      = "bytes_recv"
              }
            ],
            [
              {
                expression = "SEARCH('{EC2/LabMonitoring,InstanceId} MetricName=\"bytes_sent\"', 'Sum', 60)"
                id         = "net_sent"
                label      = "bytes_sent"
              }
            ]
          ]
        }
      },

      {
        type   = "metric"
        x      = 0
        y      = 15
        width  = 24
        height = 6
        properties = {
          title      = "Disk IO (all EC2s)"
          region     = var.aws_region
          period     = 60
          stat       = "Average"
          view       = "timeSeries"
          stacked    = false
          liveData    = true
          metrics = [
            [
              {
                expression = "SEARCH('{EC2/LabMonitoring,InstanceId} MetricName=\"io_time\"', 'Average', 60)"
                id         = "disk_io"
                label      = "io_time"
              }
            ]
          ]
        }
      }
    ]
  })
}
