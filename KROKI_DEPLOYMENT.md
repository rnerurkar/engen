# Kroki Service Deployment Guide (Google Cloud Run)

This guide details how to deploy the Kroki diagram rendering service to Google Cloud Run for the EnGen project.

## 1. Prerequisites

Ensure you have the Google Cloud SDK installed and authenticated:

```bash
gcloud auth login
gcloud config set project [YOUR_PROJECT_ID]
```

## 2. Docker Image Creation

Although Kroki provides a public image (`yuzutech/kroki`), we recommend creating a container in your own Artifact Registry to ensure stability and control.

### 2.1 Enable Services

```bash
gcloud services enable artifactregistry.googleapis.com run.googleapis.com
```

### 2.2 Create Artifact Registry Repository

Create a repository name `engen-images` in your preferred region (e.g., `us-central1`).

```bash
gcloud artifacts repositories create engen-images \
    --repository-format=docker \
    --location=us-central1 \
    --description="EnGen Service Images"
```

### 2.3 Build and Push

Navigate to the `kroki-service` directory containing the Dockerfile.

```bash
cd kroki-service
gcloud builds submit --tag us-central1-docker.pkg.dev/[YOUR_PROJECT_ID]/engen-images/kroki:latest .
```

*Note: Replace `[YOUR_PROJECT_ID]` with your actual GCP project ID.*

## 3. Deploy to Cloud Run

Deploy the service to Cloud Run. Since this is an internal rendering service for the agent swarm, we can either make it public (protected by IAM) or internal-only (VPC). For simplicity in this guide, we show a publicly accessible (unauthenticated for demo, or authenticated for prod) deployment.

### 3.1 Deployment Command

```bash
gcloud run deploy kroki-service \
    --image us-central1-docker.pkg.dev/[YOUR_PROJECT_ID]/engen-images/kroki:latest \
    --platform managed \
    --region us-central1 \
    --port 8000 \
    --memory 1Gi \
    --cpu 1 \
    --allow-unauthenticated
```

**Security Note**: Using `--allow-unauthenticated` makes the endpoint public. For a production secure environment:
1.  Remove `--allow-unauthenticated`.
2.  Grant the Service Account used by `inference-service` the `run.invoker` role on this Cloud Run service.

### 3.2 Verify Deployment

Get the service URL:

```bash
gcloud run services describe kroki-service --region us-central1 --format "value(status.url)"
```

Test it with a simple diagram:
```bash
# Example: Encode 'graph TD; A-->B' to base64
# In python: base64.urlsafe_b64encode(zlib.compress(b'graph TD; A-->B'))
# Easier: Just check the health check
curl [SERVICE_URL]/health
```

## 4. Update EnGen Configuration

Once deployed, update the environment configuration for the `inference-service` to use this new endpoint.

### 4.1 Update .env or Cloud Run Env Vars

Set `KROKI_ENDPOINT` to your new Cloud Run URL.

**Local .env:**
```ini
KROKI_ENDPOINT=https://kroki-service-xyz-uc.a.run.app
```

**Inference Service Cloud Run Update:**
If your inference service is also on Cloud Run:

```bash
gcloud run services update inference-service \
    --region us-central1 \
    --update-env-vars KROKI_ENDPOINT=[YOUR_KROKI_URL]
```

## 5. Troubleshooting

-   **503 Service Unavailable**: Check if the container failed to start (logs). Usually insufficient memory (Kroki uses Java/Headless Chrome). Try increasing memory to 2Gi.
-   **Rendering Fails**: Ensure the Mermaid code is valid. Check logs in Cloud Run: `gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=kroki-service" --limit 20`
