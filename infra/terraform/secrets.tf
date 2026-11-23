# Shell only -- the actual secret value is added out-of-band via
# `gcloud secrets versions add`, never through Terraform (would land in state
# in plaintext) and never committed to the repo.
resource "google_secret_manager_secret" "openai_api_key" {
  project   = var.project_id
  secret_id = "openai-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_iam_member" "agent_workload_secret_accessor" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.openai_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent_workload.email}"
}
