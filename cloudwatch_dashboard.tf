resource "aws_cloudwatch_dashboard" "ec2_dashboard" {
  dashboard_name = "EC2-GoldenAMI-Dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 2

        properties = {
          markdown = <<-MD
          # EC2 Lab Monitoring
          Namespace: `EC2/LabMonitoring`
          MD
        }
      },

      {
        type   = "metric"
        x      = 0
        y      = 2
        width  = 12
        height = 6

        properties = {
          title     = "CPU Usage"
          region    = var.aws_region
          period    = 60
          stat      = "Average"
          view      = "timeSeries"
          liveData  = true
          stacked   = false
          metrics = [
            {
              expression = "SEARCH('{EC2/LabMonitoring,InstanceId} MetricName=\"cpu_usage_user\"', 'Average', 60)"
              id         = "e1"
              label      = "cpu_usage_user"
            }
          ]
        }
      },

      {
        type   = "metric"
        x      = 12
        y      = 2
        width  = 12
        height = 6

        properties = {
          title     = "Memory Usage (%)"
          region    = var.aws_region
          period    = 60
          stat      = "Average"
          view      = "timeSeries"
          liveData  = true
          stacked   = false
          metrics = [
            {
              expression = "SEARCH('{EC2/LabMonitoring,InstanceId} MetricName=\"mem_used_percent\"', 'Average', 60)"
              id         = "e2"
              label      = "mem_used_percent"
            }
          ]
        }
      },

      {
        type   = "metric"
        x      = 0
        y      = 8
        width  = 12
        height = 6

        properties = {
          title     = "Disk Usage (%)"
          region    = var.aws_region
          period    = 60
          stat      = "Average"
          view      = "timeSeries"
          liveData  = true
          stacked   = false
          metrics = [
            {
              expression = "SEARCH('{EC2/LabMonitoring,InstanceId} MetricName=\"used_percent\"', 'Average', 60)"
              id         = "e3"
              label      = "used_percent"
            }
          ]
        }
      },

      {
        type   = "metric"
        x      = 12
        y      = 8
        width  = 12
        height = 6

        properties = {
          title     = "Network Traffic"
          region    = var.aws_region
          period    = 60
          stat      = "Sum"
          view      = "timeSeries"
          liveData  = true
          stacked   = false
          metrics = [
            {
              expression = "SEARCH('{EC2/LabMonitoring,InstanceId} MetricName=\"bytes_recv\"', 'Sum', 60)"
              id         = "e4"
              label      = "bytes_recv"
            },
            {
              expression = "SEARCH('{EC2/LabMonitoring,InstanceId} MetricName=\"bytes_sent\"', 'Sum', 60)"
              id         = "e5"
              label      = "bytes_sent"
            }
          ]
        }
      }
    ]
  })
}
