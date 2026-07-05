# ── market-data table ─────────────────────────────────────────────────────
# Owned exclusively by market-data-service.
# PK: symbol (partition key)  SK: timestamp (sort key)
# Access patterns:
#   - save_bars    → BatchWriteItem PK=symbol, SK=timestamp
#   - get_bars_asc → Query PK=symbol, SK between start and end
resource "aws_dynamodb_table" "market_data" {
  name         = "${var.name}-market-data"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "symbol"
  range_key    = "timestamp"

  attribute {
    name = "symbol"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  # DB-level TTL for long-term retention (default 90 days).
  # Complements the app-level ElastiCache 300s TTL — two independent layers.
  # market-data-service sets expires_at = now + (var.dynamodb_market_data_ttl_days * 86400)
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = merge(var.tags, { Service = "market-data-service" })
}

# ── signals table ─────────────────────────────────────────────────────────
# Owned exclusively by strategy-service.
# PK: symbol (partition key)  SK: timestamp_strategy (sort key)
# Composite SK format: "2026-06-26T04:00:00Z#MinMaxWindow"
# Allows multiple strategies to store signals for the same bar without collision.
# Access patterns:
#   - write signal → PutItem PK=symbol, SK=timestamp#strategy_name
#   - read signals → Query PK=symbol, SK begins_with timestamp
resource "aws_dynamodb_table" "signals" {
  name         = "${var.name}-signals"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "symbol"
  range_key    = "timestamp_strategy"

  attribute {
    name = "symbol"
    type = "S"
  }

  attribute {
    name = "timestamp_strategy"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = merge(var.tags, { Service = "strategy-service" })
}
