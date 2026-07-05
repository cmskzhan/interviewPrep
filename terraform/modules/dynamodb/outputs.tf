output "market_data_table_name" {
  description = "DynamoDB market data table name — owned by market-data-service"
  value       = aws_dynamodb_table.market_data.name
}

output "market_data_table_arn" {
  description = "DynamoDB market data table ARN — used in IRSA policies"
  value       = aws_dynamodb_table.market_data.arn
}

output "signals_table_name" {
  description = "DynamoDB signals table name — owned by strategy-service"
  value       = aws_dynamodb_table.signals.name
}

output "signals_table_arn" {
  description = "DynamoDB signals table ARN — used in IRSA policies"
  value       = aws_dynamodb_table.signals.arn
}
