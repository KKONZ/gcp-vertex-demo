resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.region
  repository_id = "gcp-vertex-demo"
  format        = "DOCKER"
  description   = "Container images for the agent/frontend services (and, later, model-serving/embedding-service)."

  depends_on = [google_project_service.required]
}
