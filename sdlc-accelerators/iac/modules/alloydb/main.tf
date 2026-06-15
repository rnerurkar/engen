# AlloyDB task store module — scaffolded by SDLC Accelerators
variable "cluster_id" { type = string }
variable "region"     { type = string }
variable "cmek_key"   { type = string }

resource "google_alloydb_cluster" "task_store" {
  cluster_id = var.cluster_id
  location   = var.region
  encryption_config { kms_key_name = var.cmek_key }  # CMEK
}

output "cluster_name" { value = google_alloydb_cluster.task_store.name }
