output "eks_cluster_name" {
  description = "EKS cluster name — use with: aws eks update-kubeconfig --name <value>"
  value       = aws_eks_cluster.main.name
}

output "eks_cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "eks_cluster_certificate_authority" {
  description = "Base64-encoded CA data for the EKS cluster"
  value       = aws_eks_cluster.main.certificate_authority[0].data
  sensitive   = true
}

output "redis_primary_endpoint" {
  description = "ElastiCache Redis primary endpoint — inject as REDIS_URL in pods (rediss:// = TLS)"
  value       = "rediss://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379"
  sensitive   = true
}

output "dynamodb_market_data_table" {
  description = "DynamoDB market data table name — owned by market-data-service"
  value       = aws_dynamodb_table.market_data.name
}

output "dynamodb_signals_table" {
  description = "DynamoDB signals table name — owned by strategy-service"
  value       = aws_dynamodb_table.signals.name
}

output "market_data_service_role_arn" {
  description = "IRSA role ARN for market-data-service. Annotate the Kubernetes ServiceAccount with: eks.amazonaws.com/role-arn=<value>"
  value       = aws_iam_role.market_data_service.arn
}

output "strategy_service_role_arn" {
  description = "IRSA role ARN for strategy-service. Annotate the Kubernetes ServiceAccount with: eks.amazonaws.com/role-arn=<value>"
  value       = aws_iam_role.strategy_service.arn
}
