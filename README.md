# terraform-infra

**Purpose:** Full Infrastructure-as-Code repository using Terraform with CI/CD (Jenkins), Ansible configuration, reusable modules, and tooling to provision, configure, test, monitor, and operate cloud infrastructure.
---

## Table of contents

1. [Project summary & goals](#project-summary--goals)
2. [Quickstart (dev & CI)](#quickstart-dev--ci)
3. [High-level architecture](#high-level-architecture)
4. [Repository layout (detailed)](#repository-layout-detailed)
5. [Terraform conventions & module standards](#terraform-conventions--module-standards)
6. [Backends, state & locking](#backends-state--locking)
7. [CI/CD (Jenkins) — production-ready pipeline](#cicd-jenkins--production-ready-pipeline)
8. [GitHub Actions — optional PR checks](#github-actions--optional-pr-checks)
9. [Ansible integration & inventory generation](#ansible-integration--inventory-generation)
10. [Testing, linting & security scans](#testing-linting--security-scans)
11. [Secrets & credential management](#secrets--credential-management)
12. [Monitoring, logging & alerting](#monitoring-logging--alerting)
13. [Cost controls & tagging standards](#cost-controls--tagging-standards)
14. [IAM / least-privilege for CI/CD](#iam--least-privilege-for-cicd)
15. [Environments & branching strategy](#environments--branching-strategy)
16. [Developer workflows & dev-box](#developer-workflows--dev-box)
17. [Contribution guide & PR checklist](#contribution-guide--pr-checklist)
18. [Operational runbook & disaster recovery](#operational-runbook--disaster-recovery)
19. [Troubleshooting & FAQ](#troubleshooting--faq)
20. [Appendix: useful snippets & templates](#appendix-useful-snippets--templates)
21. [License & acknowledgements](#license--acknowledgements)

---

# Project summary & goals

This repository codifies the full lifecycle for cloud infrastructure:

* Provision VPC, compute (EC2/EKS), databases, IAM, and security tooling via Terraform modules.
* Automate plan/apply lifecycle using Jenkins (production ready).
* Configure provisioned machines with Ansible (post-provisioning).
* Enforce quality via linting, static analysis, and automated tests.
* Manage remote state securely with locking and versioning.
* Provide runbooks, troubleshooting, PR templates, and contribution guidance.

Primary goals:

* Repeatable, auditable, and safe infrastructure changes.
* Minimal human error and clear audit trail for production changes.
* Keep secrets out of source control, use least-privilege for automation.

---

# Quickstart (dev & CI)

## Local (developer)

1. Install Terraform (use `tfenv` to pin version used in CI).
2. Clone repo and `cd` into root.
3. Copy an example env file and edit:

```bash
cp environments/example.tfvars environments/dev.tfvars
# edit environments/dev.tfvars
```

4. Initialize locally (no backend):

```bash
terraform init -backend=false
terraform fmt -recursive
terraform validate
terraform plan -var-file=environments/dev.tfvars
```

5. Apply for local/dev:

```bash
terraform apply -var-file=environments/dev.tfvars
```

## CI (Jenkins)

* Push/PR triggers Jenkins pipeline.
* Pipeline runs formatting, validation, security scans, `terraform plan` (artifact), manual approval for prod, then `terraform apply` using the plan artifact.
* Post-apply: pipeline runs Ansible, smoke tests, and notifies teams.

---

# High-level architecture

```
Developer -> GitHub -> Jenkins (pipeline) -> Terraform -> Cloud Provider (VPC, EC2/EKS, RDS, IAM)
                                         -> Terraform outputs -> Jenkins -> Ansible -> configure instances
                                         -> Monitoring & Logging -> Alerts -> Slack/Teams/PagerDuty

State: S3 Bucket (tfstate) + DynamoDB (locking) OR Terraform Cloud/Enterprise
Secrets: HashiCorp Vault / AWS Secrets Manager
```

Principles:

* One state per environment (or clearly separated keys).
* Module-first design for reusability.
* CI produces artifacts (plan, outputs) for auditability.

---

# Repository layout (detailed)

* `ansible/` — Ansible playbooks, roles, and example inventory templates.
* `backends/` — backend config templates for S3 + DynamoDB or other backends.
* `jenkins/` — Jenkins pipeline templates, helper shell/python scripts, credential mapping doc.
* `modules/` — Terraform modules (e.g., `vpc/`, `ec2/`, `eks/`, `rds/`, `iam/`), each with `main.tf`, `variables.tf`, `outputs.tf`, `README.md` and `examples/`.
* `pipeline/` — helper scripts for pipeline (e.g., `get_inventory.sh`, `plan_summary.py`, `run_smoke_tests.sh`).
* `payloads/` — sample JSON payloads used by automation or testing.
* `environments/` — environment-specific `*.tfvars` (`dev.tfvars`, `staging.tfvars`, `prod.tfvars`).
* `scripts/` — helper local scripts (`format-check.sh`, `validate-terraform.sh`, `bootstrap.sh`).
* `main.tf`, `variables.tf`, `outputs.tf` — root orchestration for environments.
* `client-access-key.pub` — public SSH key (never commit private keys).

---

# Terraform conventions & module standards

* Each module must have:

  * `main.tf` (resources)
  * `variables.tf` (typed variables with descriptions; mark secrets `sensitive = true`)
  * `outputs.tf` (well-named outputs)
  * `README.md` with example usage and input/output documentation
  * `examples/` directory with a minimal working example
* Pin Terraform and provider versions in root and modules:

```hcl
terraform {
  required_version = ">= 1.3.0, < 2.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 4.0" }
  }
}
```

* Adopt a tagging standard: `Project`, `Env`, `Owner`, `CostCenter`.
* Keep `main.tf` minimal; use modules to compose resources.
* Avoid embedding secrets directly in `.tfvars` committed to repo.

---

# Backends, state & locking

**Recommended backend (AWS S3 + DynamoDB) using region `eu-central-1`:**

* S3 bucket to store `.tfstate`
* DynamoDB table for locks
* S3 bucket versioning and server-side encryption enabled

**Example backend config - `backends/s3-backend.tfbackend`**

```hcl
bucket         = "my-terraform-state-bucket"
key            = "terraform-infra/${var.env}/terraform.tfstate"
region         = "eu-central-1"
dynamodb_table = "terraform-locks"
encrypt        = true
```

**Init example (scripted)**

```bash
terraform init \
  -backend-config="bucket=${S3_BUCKET}" \
  -backend-config="key=environments/${ENV}/terraform.tfstate" \
  -backend-config="region=eu-central-1" \
  -reconfigure
```

Recommendations:

* Use separate state objects per environment (`environments/dev/terraform.tfstate`, etc.).
* Enable S3 versioning and encryption and limit access via IAM policies.
* Prefer Terraform Cloud/Enterprise for teams that want RBAC and remote runs.

---

# CI/CD (Jenkins) — production-ready pipeline

**Goals:** Lint & validate, run security scans, produce immutable plan artifact, require approval for production, apply using binary plan, run Ansible, run smoke tests, archive artifacts & reports.

**Recommended Jenkins credential IDs**

* `aws-creds` — AWS access key/secret or use IAM role on Jenkins agents
* `ssh-deploy-key` — SSH private key for Ansible
* `s3-backend-bucket` — S3 backend bucket name (string)
* `slack-webhook` — notifications
* `github-token` — optional: post comments on PRs

**Opinionated `Jenkinsfile` (place under `jenkins/Jenkinsfile` or repo root):**

```groovy
pipeline {
  agent { label 'terraform' } // or a docker agent image that contains terraform & ansible
  environment {
    TF_IN_AUTOMATION = '1'
    AWS_REGION = "${params.AWS_REGION ?: 'eu-central-1'}"
  }
  options {
    ansiColor('xterm')
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '30'))
  }
  parameters {
    choice(name: 'ENV', choices: ['dev','staging','prod'], description: 'Target environment')
    booleanParam(name: 'AUTO_APPLY', defaultValue: false, description: 'Auto apply without approval')
  }
  stages {
    stage('Checkout') { steps { checkout scm } }

    stage('Tool Versions & Prechecks') {
      steps {
        sh 'terraform -version'
        sh 'ansible --version || true'
        sh './scripts/format-check.sh || true'
        sh './scripts/validate-terraform.sh || true'
      }
    }

    stage('Init Backend') {
      steps {
        dir('terraform') {
          withCredentials([string(credentialsId: 's3-backend-bucket', variable: 'S3_BUCKET')]) {
            sh '''
              terraform init -input=false \
                -backend-config="bucket=${S3_BUCKET}" \
                -backend-config="key=environments/${ENV}/terraform.tfstate" \
                -backend-config="region=eu-central-1" \
                -reconfigure
            '''
          }
        }
      }
    }

    stage('Plan & Security Scans') {
      steps {
        dir('terraform') {
          sh "terraform workspace select ${ENV} || terraform workspace new ${ENV}"
          sh "terraform plan -input=false -var-file=../environments/${ENV}.tfvars -out=planfile"
          sh "tflint --init || true"
          sh "tflint || true"
          sh "tfsec . || true"
          sh "checkov -d . || true"
          sh "terraform show -json planfile > plan.json || true"
        }
        archiveArtifacts artifacts: 'terraform/planfile,terraform/plan.json', allowEmptyArchive: true
      }
    }

    stage('Manual Approval (prod)') {
      when { expression { params.ENV == 'prod' && !params.AUTO_APPLY } }
      steps {
        timeout(time: 2, unit: 'HOURS') {
          input message: "Approve apply to ${params.ENV}?", ok: 'Apply'
        }
      }
    }

    stage('Apply') {
      steps {
        dir('terraform') {
          sh "terraform apply -input=false planfile"
        }
      }
    }

    stage('Collect Outputs & Ansible') {
      steps {
        dir('terraform') {
          sh "terraform output -json > outputs_${params.ENV}.json || true"
          archiveArtifacts artifacts: "terraform/outputs_${params.ENV}.json"
        }
        dir('ansible') {
          sh "../pipeline/get_inventory.sh ../terraform/outputs_${params.ENV}.json > inventory.ini || true"
          sh "ansible-playbook -i inventory.ini playbooks/site.yml --private-key ~/.ssh/deploy_key -e env=${params.ENV} || true"
        }
      }
    }

    stage('Smoke Tests & Notify') {
      steps {
        sh "./pipeline/run_smoke_tests.sh ${params.ENV} || true"
        // add notification steps here
      }
    }
  }

  post {
    always {
      archiveArtifacts artifacts: 'terraform/*.tfstate', allowEmptyArchive: true
      junit 'reports/**/*.xml'
    }
    success {
      // slack/teams notification
    }
    failure {
      // slack/teams notification
    }
  }
}
```

**Key features explained**

* Produce and archive `planfile` and `plan.json` (immutable plan applied later).
* Run `tflint`, `tfsec`, and `checkov` to catch issues early.
* Manual `input` approval for `prod`.
* Use Jenkins credentials to retrieve backend bucket names and SSH keys.
* Run Ansible with an inventory derived from Terraform outputs.

---

# GitHub Actions — optional PR checks

Use GitHub Actions for fast PR-level checks (format, validate, lint, security scans). Keep Jenkins for stateful `plan` + `apply`.

**`.github/workflows/terraform-pr.yml` (concept):**

```yaml
name: terraform-pr
on: [pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: 1.5.0
      - name: terraform fmt
        run: terraform fmt -check -recursive
      - name: init & validate
        run: terraform init -backend=false && terraform validate
      - name: tflint
        uses: wata727/tflint-action@v0.2.1
      - name: tfsec
        uses: aquasecurity/tfsec-action@v1
      - name: checkov
        uses: bridgecrewio/checkov-action@master
```

---

# Ansible integration & inventory generation

**Workflow**

1. Terraform outputs instance info: `terraform output -json > outputs.json`.
2. Pipeline converts outputs to Ansible inventory (`inventory.ini`).
3. Ansible runs playbooks/roles using SSH key stored in Jenkins credentials.

**Example `pipeline/get_inventory.sh`**

```bash
#!/usr/bin/env bash
OUT_JSON="$1"
jq -r '.web_instances.value[] | "\(.public_ip) ansible_host=\(.public_ip) ansible_user=ubuntu"' < "$OUT_JSON"
```

**Example `ansible/playbooks/site.yml`**

```yaml
- hosts: all
  become: true
  roles:
    - role: common
    - role: monitoring-agent
```

Best practices:

* Make roles idempotent.
* Use `ansible-lint` and `molecule` for role testing.
* Retrieve secrets for playbooks from Vault/SSM when needed.

---

# Testing, linting & security scans

**Checks run in pipeline / locally:**

* `terraform fmt -check -recursive`
* `terraform validate`
* `tflint`
* `tfsec`
* `checkov`
* `infracost` (cost estimate)
* `ansible-lint` and `molecule` for Ansible roles

**Automated testing**

* Unit / integration testing using Terratest (Go) or kitchen-terraform.
* Integration tests run in ephemeral test environment, then destroy resources.

**Example Terratest skeleton (in `test/`):**

```go
package test
import (
  "testing"
  "github.com/gruntwork-io/terratest/modules/terraform"
)
func TestExample(t *testing.T) {
  opts := &terraform.Options{TerraformDir: "../modules/ec2/example"}
  defer terraform.Destroy(t, opts)
  terraform.InitAndApply(t, opts)
  // assertions...
}
```

---

# Secrets & credential management

**Principles**

* Do not commit secrets or private keys.
* Use short-lived credentials from Vault when possible.
* For AWS, use IAM roles for Jenkins agents or AWS credentials stored securely in Jenkins Credentials.

**Recommended stores**

1. HashiCorp Vault — best for dynamic secrets and rotation.
2. Cloud provider secret managers (AWS Secrets Manager / SSM Parameter Store).
3. Jenkins Credentials store (SSH keys, tokens) — used only at runtime by the pipeline.

If a secret is accidentally committed: rotate immediately, scrub history using `git filter-repo` / `bfg`, and notify stakeholders.

---

# Monitoring, logging & alerting

**What to collect**

* System logs and application logs into a centralized log store.
* Metrics: CPU, memory, disk, request latency, error rates.
* Health checks and availability metrics.

**Recommended stack**

* EC2: CloudWatch agent or Datadog agent.
* Kubernetes/EKS: Prometheus + Grafana + Alertmanager (kube-prometheus-stack).
* Centralized logs: EFK (Elasticsearch / Fluentd / Kibana) or hosted solution (Datadog, Logz).

**Alerting**

* Create alarm rules for critical events (instance down, job failures, high error rates).
* Integrate alerts with Slack/Teams and PagerDuty for on-call escalation.

---

# Cost controls & tagging standards

**Tagging**

* Enforce tags: `Project`, `Env`, `Owner`, `CostCenter`, `BillingCode`.

**Cost tools**

* Use `infracost` in PRs to surface cost deltas before merging.
* Define budgets and alerts in cloud provider (AWS Budgets -> SNS notifications).

**Recommendations**

* Use auto-scaling with sensible limits.
* Turn off dev environment resources when idle (schedule or ephemeral environments).

---

# IAM / least-privilege for CI/CD

**CI/CD minimal permissions (example, AWS, region eu-central-1)**:

* S3: `GetObject`, `PutObject`, `ListBucket` for state bucket
* DynamoDB: CRUD for lock table
* EC2: `DescribeInstances`, optionally `RunInstances`/`TerminateInstances` if Terraform provisions instances
* Secrets Manager/SSM Get access if pipeline reads secrets
* Limit all resource ARNs to the narrowest scope possible

**Sample policy snippet**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:PutObject","s3:ListBucket"],
      "Resource": ["arn:aws:s3:::my-terraform-state-bucket","arn:aws:s3:::my-terraform-state-bucket/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem","dynamodb:PutItem","dynamodb:DeleteItem","dynamodb:Query","dynamodb:UpdateItem"],
      "Resource": ["arn:aws:dynamodb:eu-central-1:123456789012:table/terraform-locks"]
    }
  ]
}
```

---

# Environments & branching strategy

* `main` — protected, merges automatically trigger `prod` flow (with manual approval).
* `develop` or `staging` — integration/staging environment.
* `feature/*` — developer features (mapped to `dev` environment).

**Mapping**

* `feature/*` -> `dev`
* `develop` -> `staging`
* `main` -> `prod`

**Protection**

* Require PRs with at least one approver for `main`.
* Require passing CI checks before merge.

---

# Developer workflows & dev-box

**Dev-box recommendations**

* Docker image with pinned Terraform, tflint, tfsec, checkov, ansible, python3, jq installed.
* Provide `Makefile` to speed up common tasks:

```makefile
init:
    terraform init -backend=false

fmt:
    terraform fmt -recursive

plan:
    terraform plan -var-file=environments/dev.tfvars

validate:
    terraform validate
```

**Local test flow**

* `make fmt && make validate && make plan` before opening PR.

---

# Contribution guide & PR checklist

**How to contribute**

* Fork repo, create `feature/<short-desc>`, open PR to `develop` or `main` depending on change.
* Include a clear description and testing steps.

**PR checklist (add in `.github/pull_request_template.md`)**

* [ ] `terraform fmt -check` passed
* [ ] `terraform validate` passed
* [ ] `tflint` executed
* [ ] `tfsec` / `checkov` executed and findings reviewed
* [ ] Module docs updated (if module changed)
* [ ] Plan artifact (CI) included or pipeline must run plan

**CODEOWNERS**

* Add `CODEOWNERS` to enforce reviewers for modules and directories.

---

# Operational runbook & disaster recovery

**Common playbooks**

* **State corruption**: restore `.tfstate` from S3 object versioning snapshots; re-run `terraform plan` and `terraform apply` against restored state.
* **Stuck lock**: use `terraform force-unlock <LOCK_ID>` after confirming no active apply is running.
* **Secrets leak**: rotate compromised secrets immediately and scrub Git history.
* **Region outage**: use cross-region backups (RDS snapshots, S3 cross-region replication) and a documented DR runbook to re-deploy in the DR region using DR-specific `tfvars`.

**Backups**

* Enable RDS automated snapshots.
* Enable S3 versioning for Terraform state.

---

# Troubleshooting & FAQ

**Plan differs from apply**

* Ensure apply uses the exact `planfile` produced by plan.
* Ensure same provider versions and same variable files are used.

**State locked**

* Inspect DynamoDB lock table; if stale, `terraform force-unlock` may be necessary.

**Secrets found in repo**

* Rotate immediately, scrub repository history, notify stakeholders and rotate any exposed credentials.

---

# Appendix: useful snippets & templates

## `scripts/format-check.sh`

```bash
#!/usr/bin/env bash
set -e
terraform fmt -check -recursive
```

## `pipeline/get_inventory.sh`

```bash
#!/usr/bin/env bash
OUT_JSON="$1"
jq -r '.web_instances.value[] | "\(.public_ip) ansible_host=\(.public_ip) ansible_user=ubuntu"' < "$OUT_JSON"
```

## `pipeline/plan_summary.py`

```python
#!/usr/bin/env python3
import json, sys
p = json.load(open(sys.argv[1]))
changes = p.get('resource_changes', [])
adds = sum(1 for r in changes if r['change']['actions'] == ['create'])
mods = sum(1 for r in changes if r['change']['actions'] == ['update'])
dels = sum(1 for r in changes if r['change']['actions'] == ['delete'])
print(f"Adds: {adds}, Mods: {mods}, Dels: {dels}")
```

## Example root `variables.tf` snippet

```hcl
variable "env" {
  description = "Target environment"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}
```

## Example backend config `backends/s3-backend.tfbackend`

```hcl
bucket         = "my-terraform-state-bucket"
key            = "terraform-infra/${var.env}/terraform.tfstate"
region         = "eu-central-1"
dynamodb_table = "terraform-locks"
encrypt        = true
```

---

# License & acknowledgements

Add your preferred license (e.g. `MIT`, `Apache-2.0`) and acknowledge any third-party modules or templates you used. If you incorporate external examples or guides, cite them in a `REFERENCES.md` file.

---

## Next steps I recommend (pick any)

* Replace placeholder names (S3 bucket, ARNs, email addresses) with your real values.
* Add `.github/pull_request_template.md` and `CODEOWNERS`.
* Add a short `README_TLDR.md` for the repo root that links to this full README saved in `docs/README_FULL.md`.
* If you want, paste your `Jenkinsfile`, `main.tf`, and `variables.tf` here and I'll produce a tailored `README.md` that exactly matches variable names and pipeline steps.
