variable "name" {
  description = "Name prefix for all resources (e.g. millenium-dev)"
  type        = string
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for EKS nodes"
  type        = list(string)
}

variable "eks_cluster_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.30"
}

variable "eks_node_instance_types" {
  description = "EC2 instance types for the EKS managed node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "eks_node_desired_size" {
  description = "Desired number of EKS worker nodes"
  type        = number
}

variable "eks_node_min_size" {
  description = "Minimum number of EKS worker nodes"
  type        = number
}

variable "eks_node_max_size" {
  description = "Maximum number of EKS worker nodes"
  type        = number
}
