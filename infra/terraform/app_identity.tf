# Runtime identity for the agent pods -- separate from github-deployer above.
# This is what makes "read secrets at runtime via the pod's own GKE Workload
# Identity" (docs/architecture.md) real: the KSA named var.agent_ksa_name in
# var.gke_namespace impersonates this GCP SA with no key material anywhere.
resource "google_service_account" "agent_workload" {
  project      = var.project_id
  account_id   = "agent-workload"
  display_name = "Agent service runtime identity"
}

resource "google_project_iam_member" "agent_workload_bigquery_jobuser" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.agent_workload.email}"
}

# Workload Identity binding: the Kubernetes ServiceAccount (not a key file)
# is the only thing authorized to impersonate this GCP SA.
resource "google_service_account_iam_member" "agent_workload_wif_user" {
  service_account_id = google_service_account.agent_workload.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${var.gke_namespace}/${var.agent_ksa_name}]"
}
