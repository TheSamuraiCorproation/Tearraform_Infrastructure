resource "aws_cloudwatch_dashboard" "ec2_dashboard" {
  dashboard_name = "EC2-GoldenAMI-Dashboard"

  dashboard_body = jsonencode({
    widgets = flatten([
      for instance_name, instance_id in module.ec2[0].ec2_instance_ids : [
        # CPU & Network Widget
        {
          type   = "metric"
          x      = 0
          y      = 0
          width  = 12
          height = 6
          properties = {
            metrics = [
              ["AWS/EC2", "CPUUtilization", "InstanceId", instance_id],
              ["AWS/EC2", "NetworkIn", "InstanceId", instance_id],
              ["AWS/EC2", "NetworkOut", "InstanceId", instance_id]
            ]
            period = 300
            stat   = "Average"
            region = var.aws_region
            title  = "${instance_name} CPU & Network"
          }
        },
        # Disk I/O Widget
        {
          type   = "metric"
          x      = 0
          y      = 6
          width  = 12
          height = 6
          properties = {
            metrics = [
              ["AWS/EC2", "DiskReadBytes", "InstanceId", instance_id],
              ["AWS/EC2", "DiskWriteBytes", "InstanceId", instance_id]
            ]
            period = 300
            stat   = "Sum"
            region = var.aws_region
            title  = "${instance_name} Disk I/O"
          }
        }
      ]
    ])
  })
}
