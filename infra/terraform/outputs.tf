output "gke_cluster_name" {
  value = google_container_cluster.primary.name
}

output "gke_cluster_endpoint" {
  value     = google_container_cluster.primary.endpoint
  sensitive = true
}

output "artifact_registry_repo" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "github_deployer_sa_email" {
  value = google_service_account.github_deployer.email
}

output "agent_workload_sa_email" {
  value = google_service_account.agent_workload.email
}

output "workload_identity_provider" {
  description = "Full resource name for the google-github-actions/auth `workload_identity_provider` input."
  value       = google_iam_workload_identity_pool_provider.github_provider.name
}
