aws_region  = "us-east-1"
project     = "millenium"
environment = "prod"

# EKS scaling — prod: double dev (desired, max); min_size unchanged
eks_cluster_version     = "1.30"
eks_node_instance_types = ["t3.medium"]
eks_node_desired_size   = 4  # dev=2 × 2
eks_node_min_size       = 1  # same as dev
eks_node_max_size       = 8  # dev=4 × 2

# ElastiCache
elasticache_node_type = "cache.t3.micro"

# DynamoDB
dynamodb_market_data_ttl_days = 90
