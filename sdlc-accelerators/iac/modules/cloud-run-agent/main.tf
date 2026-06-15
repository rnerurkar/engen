# Cloud Run agent module — generated/scaffolded by SDLC Accelerators
# NEVER-SWAPPABLE alignment: Binary Authorization enforced at deploy.

variable "service_name" { type = string }
variable "region"       { type = string }
variable "image"        { type = string }
variable "service_account_email" { type = string }
variable "min_instances" { type = number, default = 1 }
variable "max_instances" { type = number, default = 20 }

resource "google_cloud_run_v2_service" "agent" {
  name     = var.service_name
  location = var.region

  template {
    service_account = var.service_account_email
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }
    containers {
      image = var.image
    }
    # CMEK + VPC-SC applied at project level.
  }

  # Binary Authorization (NEVER-SWAPPABLE) enforced via project policy.
}

output "uri" { value = google_cloud_run_v2_service.agent.uri }
