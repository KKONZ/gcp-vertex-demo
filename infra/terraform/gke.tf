# GKE Autopilot: proves GPU-backed self-hosted inference (requested directly in
# the pod spec -- nvidia-l4/nvidia-tesla-t4 -- no separate node-pool resource
# needed here). The local kind cluster covers the CPU-only pieces instead; see
# infra/k8s/overlays/kind vs. overlays/gke, and docs/architecture.md.
resource "google_container_cluster" "primary" {
  project  = var.project_id
  name     = "gcp-vertex-demo"
  location = var.region

  enable_autopilot = true

  # This is a demo cluster meant to be torn down -- don't let Terraform's
  # default deletion protection block that.
  deletion_protection = false

  release_channel {
    channel = "REGULAR"
  }

  depends_on = [google_project_service.required]
}
