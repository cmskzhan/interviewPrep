# Security group — allow Redis port only from EKS cluster nodes
resource "aws_security_group" "elasticache" {
  name        = "${local.name}-elasticache-sg"
  description = "Allow Redis (6379) from EKS nodes only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Redis from EKS cluster security group"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_eks_cluster.main.vpc_config[0].cluster_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${local.name}-elasticache-sg" })
}

resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name}-elasticache-subnets"
  subnet_ids = aws_subnet.private[*].id
  tags       = local.tags
}

# Single Redis replication group shared by all services.
# Services are isolated via key namespace prefixes:
#   market-data-service → mds:<key>
#   strategy-service    → stg:<key>
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${local.name}-redis"
  description          = "Shared TTL cache — mds:* (market-data-service) and stg:* (strategy-service)"

  node_type            = var.elasticache_node_type
  num_cache_clusters   = 2 # primary + one replica; automatic_failover handles promotion
  port                 = 6379
  engine_version       = "7.1"
  parameter_group_name = "default.redis7"

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.elasticache.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true # TLS — matches rediss:// in cache.py
  automatic_failover_enabled = true

  tags = local.tags
}
