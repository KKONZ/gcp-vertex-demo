variable "project_id" {
  description = "GCP project ID backing this repo."
  type        = string
  default     = "gcp-vertex-demo-515417"
}

variable "region" {
  description = "Region for the GKE cluster, Artifact Registry, and Secret Manager replication."
  type        = string
  default     = "us-central1"
}

variable "github_repo" {
  description = "GitHub repo allowed to assume the deployer service account via WIF, as owner/repo."
  type        = string
  default     = "KKONZ/gcp-vertex-demo"
}

variable "gke_namespace" {
  description = "Kubernetes namespace the app workloads run in, used for the Workload Identity binding."
  type        = string
  default     = "vertex-demo"
}

variable "agent_ksa_name" {
  description = "Kubernetes ServiceAccount name used by the agent Deployment, bound to the agent-workload GCP SA."
  type        = string
  default     = "agent"
}
