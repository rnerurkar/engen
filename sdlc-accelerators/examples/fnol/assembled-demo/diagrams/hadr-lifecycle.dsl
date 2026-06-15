// HA/DR Lifecycle
// Strategy: Warm Standby

us_east1 [icon: region] { label: "us-east1 (Primary)" }
us_central1 [icon: region] { label: "us-central1 (DR)" }
us_east1 > us_central1: "replication"
