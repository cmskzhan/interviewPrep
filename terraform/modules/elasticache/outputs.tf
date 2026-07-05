output "redis_replication_group_arn" {
  description = "ARN of the Redis replication group"
  value       = aws_elasticache_replication_group.redis.arn
}

output "redis_primary_endpoint" {
  description = "ElastiCache Redis primary endpoint — inject as REDIS_URL in pods (rediss:// = TLS)"
  value       = "rediss://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379"
  sensitive   = true
}
