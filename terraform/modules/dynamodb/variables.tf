variable "name" {
  description = "Name prefix for all resources"
  type        = string
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "dynamodb_market_data_ttl_days" {
  description = "Days before market data bars expire at DB level"
  type        = number
  default     = 90
}
