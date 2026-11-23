# All of these were already enabled by hand before Terraform touched this project
# (confirmed via `gcloud services list --enabled`) -- these resources make that
# state explicit and idempotent, not a first-time enablement.
locals {
  required_apis = [
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "container.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "aiplatform.googleapis.com",
    "bigquery.googleapis.com",
    "compute.googleapis.com",
  ]
}

resource "google_project_service" "required" {
  for_each = toset(local.required_apis)

  project = var.project_id
  service = each.value

  # This project has other APIs enabled for unrelated work (analyticshub,
  # backupdr, etc.) -- never let `terraform destroy` touch API enablement.
  disable_on_destroy         = false
  disable_dependent_services = false
}
