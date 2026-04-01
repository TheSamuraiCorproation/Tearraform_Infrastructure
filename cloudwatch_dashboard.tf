resource "aws_cloudwatch_dashboard" "ec2_dashboard" {
  dashboard_name = "EC2-GoldenAMI-Dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        x = 0
        y = 0
        width = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", "InstanceId", "${aws_instance.this["DEMO-vm"].id}"],
            ["AWS/EC2", "NetworkIn", "InstanceId", "${aws_instance.this["DEMO-vm"].id}"],
            ["AWS/EC2", "NetworkOut", "InstanceId", "${aws_instance.this["DEMO-vm"].id}"]
          ]
          period = 300
          stat = "Average"
          region = var.aws_region
          title = "EC2 CPU & Network"
        }
      },
      {
        type = "metric"
        x = 0
        y = 6
        width = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/EC2", "DiskReadBytes", "InstanceId", "${aws_instance.this["DEMO-vm"].id}"],
            ["AWS/EC2", "DiskWriteBytes", "InstanceId", "${aws_instance.this["DEMO-vm"].id}"]
          ]
          period = 300
          stat = "Sum"
          region = var.aws_region
          title = "EC2 Disk I/O"
        }
      }
    ]
  })
}
