terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  backend "s3" {
    bucket         = "millenium-terraform-state-dev"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "millenium-terraform-locks-dev"
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  name = "${var.project}-${var.environment}"

  tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ── VPC ───────────────────────────────────────────────────────────────────
module "vpc" {
  source = "../../modules/vpc"

  name       = local.name
  tags       = local.tags
  vpc_cidr   = var.vpc_cidr
  aws_region = var.aws_region
}

# ── EKS ───────────────────────────────────────────────────────────────────
module "eks" {
  source = "../../modules/eks"

  name                    = local.name
  tags                    = local.tags
  private_subnet_ids      = module.vpc.private_subnet_ids
  eks_cluster_version     = var.eks_cluster_version
  eks_node_instance_types = var.eks_node_instance_types
  eks_node_desired_size   = var.eks_node_desired_size
  eks_node_min_size       = var.eks_node_min_size
  eks_node_max_size       = var.eks_node_max_size
}

# ── ElastiCache ───────────────────────────────────────────────────────────
module "elasticache" {
  source = "../../modules/elasticache"

  name                          = local.name
  tags                          = local.tags
  vpc_id                        = module.vpc.vpc_id
  private_subnet_ids            = module.vpc.private_subnet_ids
  eks_cluster_security_group_id = module.eks.cluster_security_group_id
  elasticache_node_type         = var.elasticache_node_type
}

# ── DynamoDB ──────────────────────────────────────────────────────────────
module "dynamodb" {
  source = "../../modules/dynamodb"

  name                          = local.name
  tags                          = local.tags
  dynamodb_market_data_ttl_days = var.dynamodb_market_data_ttl_days
}

# ── IRSA roles (service-level IAM) ───────────────────────────────────────
# TODO: As new services are added (e.g. order-service, risk-service), this
# file will grow. At that point, extract into modules/iam and accept a map
# of service_account → policy_document to keep env roots concise.
# See terraform/README.md for details.

locals {
  oidc_issuer = module.eks.oidc_issuer
}

# market-data-service — write market-data table + connect to ElastiCache
resource "aws_iam_role" "market_data_service" {
  name = "${local.name}-market-data-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = module.eks.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_issuer}:sub" = "system:serviceaccount:default:market-data-service"
          "${local.oidc_issuer}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "market_data_service" {
  name = "market-data-service-policy"
  role = aws_iam_role.market_data_service.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDBMarketDataReadWrite"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:BatchWriteItem",
          "dynamodb:UpdateItem",
        ]
        Resource = module.dynamodb.market_data_table_arn
      },
      {
        Sid      = "ElastiCacheConnect"
        Effect   = "Allow"
        Action   = ["elasticache:Connect"]
        Resource = module.elasticache.redis_replication_group_arn
      },
    ]
  })
}

# strategy-service — read market-data, write signals, connect to ElastiCache
resource "aws_iam_role" "strategy_service" {
  name = "${local.name}-strategy-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = module.eks.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_issuer}:sub" = "system:serviceaccount:default:strategy-service"
          "${local.oidc_issuer}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "strategy_service" {
  name = "strategy-service-policy"
  role = aws_iam_role.strategy_service.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDBMarketDataRead"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
        ]
        Resource = module.dynamodb.market_data_table_arn
      },
      {
        Sid    = "DynamoDBSignalsReadWrite"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
        ]
        Resource = module.dynamodb.signals_table_arn
      },
      {
        Sid      = "ElastiCacheConnect"
        Effect   = "Allow"
        Action   = ["elasticache:Connect"]
        Resource = module.elasticache.redis_replication_group_arn
      },
    ]
  })
}
