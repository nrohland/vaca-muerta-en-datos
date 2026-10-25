# Optional adoption of existing BigQuery sandbox datasets. No billable runtime.
terraform {
  required_version = ">= 1.5, < 2.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0, < 8.0"
    }
  }
  backend "local" {}
}

provider "google" {
  project = var.project_id
}

variable "project_id" {
  type    = string
  default = "vaca-muerta-pulse"
}

variable "adopt_existing_datasets" {
  description = "Opt in only after importing the four existing datasets. Never manages billing or APIs."
  type        = bool
  default     = false
}

locals {
  dataset_ids = toset([
    "raw_cap4_candidate_dev", "stg_cap4_candidate_dev",
    "int_cap4_candidate_dev", "marts_cap4_candidate_dev"
  ])
}

resource "google_bigquery_dataset" "candidate" {
  for_each   = var.adopt_existing_datasets ? local.dataset_ids : toset([])
  project    = var.project_id
  dataset_id = each.value
  location   = "US"

  lifecycle {
    prevent_destroy = true
    # First adoption preserves existing expiration, ACLs and descriptive metadata.
    ignore_changes = [access, default_table_expiration_ms, default_partition_expiration_ms, labels, description, friendly_name]
  }
}

output "managed_datasets" {
  value = keys(google_bigquery_dataset.candidate)
}
