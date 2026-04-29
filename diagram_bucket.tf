# Creates the S3 bucket that Jenkinsfile.diagram uploads SVG / PNG / HTML / .mmd
# artefacts to, and where the platform backend fetches diagram URLs from.
#
# Drop this file next to main.tf — Terraform will pick it up automatically.

# ── Bucket ──────────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "diagram_artifacts" {
  bucket = "dojo-diagram-artifacts"

  tags = {
    Project     = "DOJO"
    Component   = "DiagramGeneration"
    ManagedBy   = "Terraform"
  }
}

# ── Versioning (keeps previous renders if a lab is re-run) ──────────────────

resource "aws_s3_bucket_versioning" "diagram_artifacts" {
  bucket = aws_s3_bucket.diagram_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

# ── Allow public read so the frontend can hotlink SVG / PNG / HTML ───────────
# If your platform serves diagrams through a backend proxy instead,
# remove this block and the aws_s3_bucket_policy below, and use
# pre-signed URLs or an IAM role instead.

resource "aws_s3_bucket_public_access_block" "diagram_artifacts" {
  bucket = aws_s3_bucket.diagram_artifacts.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "diagram_artifacts" {
  bucket = aws_s3_bucket.diagram_artifacts.id

  # depends_on prevents a race with the public-access-block resource
  depends_on = [aws_s3_bucket_public_access_block.diagram_artifacts]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadDiagrams"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.diagram_artifacts.arn}/*"
      }
    ]
  })
}

# ── Lifecycle: auto-delete diagrams older than 30 days ──────────────────────

resource "aws_s3_bucket_lifecycle_configuration" "diagram_artifacts" {
  bucket = aws_s3_bucket.diagram_artifacts.id

  rule {
    id     = "expire-old-diagrams"
    status = "Enabled"

    # Only target the diagrams/ prefix so any other objects in the bucket
    # are not affected
    filter {
      prefix = "diagrams/"
    }

    expiration {
      days = 30
    }

    # Also clean up non-current versions produced by versioning
    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
}

# ── Outputs ─────────────────────────────────────────────────────────────────

output "diagram_bucket_name" {
  description = "Name of the S3 bucket that stores lab architecture diagrams"
  value       = aws_s3_bucket.diagram_artifacts.id
}

output "diagram_bucket_base_url" {
  description = "Base URL for diagram artefacts — append /diagrams/<lab_id>/lab.{svg,png,html}"
  value       = "https://${aws_s3_bucket.diagram_artifacts.id}.s3.${var.aws_region}.amazonaws.com"
}
