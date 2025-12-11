#!/bin/bash
set -e

PROJECT_ID="your-gcp-project"
REGION="us-central1"
REPO="agent-swarm"

# 1. Create Artifact Registry
gcloud artifacts repositories create $REPO --repository-format=docker --location=$REGION || true

# 2. Deploy Agents Function
deploy_agent() {
  AGENT_NAME=$1
  echo ">>> Deploying $AGENT_NAME..."
  
  # Build
  gcloud builds submit ./agents/$AGENT_NAME \
    --tag $REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$AGENT_NAME:latest
    
  # Deploy
  gcloud run deploy $AGENT_NAME \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$AGENT_NAME:latest \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars GCP_PROJECT_ID=$PROJECT_ID
    
  # Capture URL
  URL=$(gcloud run services describe $AGENT_NAME --region $REGION --format 'value(status.url)')
  echo "$AGENT_NAME URL: $URL"
  export "${AGENT_NAME^^}_URL"=$URL
}

# 3. Deploy Sub-Agents
deploy_agent "vision"
deploy_agent "retrieval"
deploy_agent "writer"
deploy_agent "reviewer"

# 4. Deploy Orchestrator (With Env Vars for Sub-Agents)
echo ">>> Deploying Orchestrator..."
gcloud builds submit ./agents/orchestrator \
  --tag $REGION-docker.pkg.dev/$PROJECT_ID/$REPO/orchestrator:latest

gcloud run deploy orchestrator \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/$REPO/orchestrator:latest \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars VISION_AGENT_URL=$VISION_URL \
  --set-env-vars RETRIEVAL_AGENT_URL=$RETRIEVAL_URL \
  --set-env-vars WRITER_AGENT_URL=$WRITER_URL \
  --set-env-vars REVIEWER_AGENT_URL=$REVIEWER_URL

echo ">>> Swarm Deployment Complete!"