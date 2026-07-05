output "eks_cluster_name" {
  description = "EKS cluster name — use with: aws eks update-kubeconfig --name <value>"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_certificate_authority" {
  description = "Base64-encoded CA data for the EKS cluster"
  value       = module.eks.cluster_certificate_authority
  sensitive   = true
}

output "redis_primary_endpoint" {
  description = "ElastiCache Redis primary endpoint — inject as REDIS_URL in pods (rediss:// = TLS)"
  value       = module.elasticache.redis_primary_endpoint
  sensitive   = true
}

output "dynamodb_market_data_table" {
  description = "DynamoDB market data table name — owned by market-data-service"
  value       = module.dynamodb.market_data_table_name
}

output "dynamodb_signals_table" {
  description = "DynamoDB signals table name — owned by strategy-service"
  value       = module.dynamodb.signals_table_name
}

output "market_data_service_role_arn" {
  description = "IRSA role ARN for market-data-service. Annotate the Kubernetes ServiceAccount with: eks.amazonaws.com/role-arn=<value>"
  value       = aws_iam_role.market_data_service.arn
}

output "strategy_service_role_arn" {
  description = "IRSA role ARN for strategy-service. Annotate the Kubernetes ServiceAccount with: eks.amazonaws.com/role-arn=<value>"
  value       = aws_iam_role.strategy_service.arn
}
