# OIDC provider — bridges Kubernetes service accounts to IAM roles (IRSA)
data "tls_certificate" "eks" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer
  tags            = local.tags
}

locals {
  oidc_issuer = trimprefix(aws_eks_cluster.main.identity[0].oidc[0].issuer, "https://")
}

# ── market-data-service ───────────────────────────────────────────────────
# Permissions: write market-data table + connect to ElastiCache
resource "aws_iam_role" "market_data_service" {
  name = "${local.name}-market-data-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.eks.arn }
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
        Resource = aws_dynamodb_table.market_data.arn
      },
      {
        Sid      = "ElastiCacheConnect"
        Effect   = "Allow"
        Action   = ["elasticache:Connect"]
        Resource = aws_elasticache_replication_group.redis.arn
      },
    ]
  })
}

# ── strategy-service ──────────────────────────────────────────────────────
# Permissions: read market-data table, write signals table, connect to ElastiCache
resource "aws_iam_role" "strategy_service" {
  name = "${local.name}-strategy-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.eks.arn }
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
        Resource = aws_dynamodb_table.market_data.arn
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
        Resource = aws_dynamodb_table.signals.arn
      },
      {
        Sid      = "ElastiCacheConnect"
        Effect   = "Allow"
        Action   = ["elasticache:Connect"]
        Resource = aws_elasticache_replication_group.redis.arn
      },
    ]
  })
}
