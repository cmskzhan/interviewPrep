# Terraform — Millenium Infrastructure

This directory contains the Terraform infrastructure for the Millenium project, organised using the **Root-Module Isolation Pattern**: shared, reusable modules live under `modules/`, and each environment has its own self-contained root module under `envs/`.

## Directory Structure

```
terraform/
├── modules/              # Reusable, environment-agnostic modules
│   ├── eks/              # EKS cluster, node group, OIDC provider + node IAM roles
│   ├── vpc/              # VPC, subnets, IGW, NAT gateway, route tables, DynamoDB endpoint
│   ├── elasticache/      # Redis replication group + security group
│   └── dynamodb/         # market-data and signals DynamoDB tables
│
└── envs/                 # Root modules — one per environment
    ├── dev/              # Development environment
    └── prod/             # Production environment
```

> Each environment root (`envs/dev`, `envs/prod`) has its **own S3 backend** and **independent state file**. Changes to one environment never affect the other.

---

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) `>= 1.5.0`
- AWS CLI configured with credentials that have sufficient IAM permissions
- S3 buckets and DynamoDB lock tables for each environment's backend must exist **before** running `init` (create them manually or via a bootstrap script):

| Environment | S3 Bucket | DynamoDB Lock Table |
|---|---|---|
| dev  | `millenium-terraform-state-dev`  | `millenium-terraform-locks-dev`  |
| prod | `millenium-terraform-state-prod` | `millenium-terraform-locks-prod` |

---

## Running Terraform

All commands must be run from inside the environment directory, **not** the repo root.

### Development

```bash
cd terraform/envs/dev

# 1. Initialise — download providers and configure the S3 backend
terraform init

# 2. Validate — check configuration syntax and internal consistency
terraform validate

# 3. Plan — preview changes without applying
terraform plan

# 4. Apply — create or update infrastructure
terraform apply
```

### Production

```bash
cd terraform/envs/prod

terraform init
terraform validate
terraform plan
terraform apply
```

> **Tip:** Always run `terraform plan` and review the diff carefully before applying to production. Consider requiring a manual approval step in CI/CD pipelines (e.g. a GitHub Environment protection rule).

---

## Environment Differences

The primary difference between environments is **EKS node group scaling**:

| Setting | Dev | Prod |
|---|---|---|
| `eks_node_desired_size` | 2 | 4 |
| `eks_node_min_size` | 1 | 1 (unchanged) |
| `eks_node_max_size` | 4 | 8 |

All scaling values are explicit in each environment's `terraform.tfvars` — no multipliers or computed overrides.

---

## IAM — Current Design and Future Direction

### Current Design

Service-level IAM roles (IRSA — IAM Roles for Service Accounts) are defined directly in each environment's `main.tf`. Currently two services have IRSA roles:

- **market-data-service** — DynamoDB read/write on `market-data` table + ElastiCache connect
- **strategy-service** — DynamoDB read on `market-data` + read/write on `signals` table + ElastiCache connect

Node-level IAM roles (EKS cluster role, node group role) are managed inside the `modules/eks` module because they are tightly coupled to the cluster lifecycle.

### Future Direction

As the application grows and new services are added (e.g. `order-service`, `risk-service`, `notification-service`), the inline IAM blocks in `main.tf` will become difficult to maintain.

**Planned change:** Extract service IAM into a dedicated `modules/iam` module that accepts a map of service accounts to policy documents:

```hcl
# Future interface — not yet implemented
module "iam" {
  source = "../../modules/iam"

  name             = local.name
  tags             = local.tags
  oidc_provider_arn = module.eks.oidc_provider_arn
  oidc_issuer      = module.eks.oidc_issuer

  service_roles = {
    "market-data-service" = {
      namespace = "default"
      policy    = data.aws_iam_policy_document.market_data_service.json
    }
    "strategy-service" = {
      namespace = "default"
      policy    = data.aws_iam_policy_document.strategy_service.json
    }
  }
}
```

This refactor should be done **before** adding a third service to avoid further duplication.

---

## Outputs

After a successful `apply`, useful values are printed as outputs. To retrieve them at any time:

```bash
# From the environment directory
terraform output eks_cluster_name
terraform output -raw redis_primary_endpoint   # sensitive — use -raw to get the plain value
terraform output market_data_service_role_arn
```

To configure `kubectl` for the deployed cluster:

```bash
aws eks update-kubeconfig \
  --region us-east-1 \
  --name $(terraform output -raw eks_cluster_name)
```
