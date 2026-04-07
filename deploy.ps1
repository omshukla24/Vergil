$ProjectID = "vergil-492601"
$RedisUrl = "rediss://default:gQAAAAAAATxrAAIncDFjYzY3MzAyZTEzZDM0OWYwOTBiOWE3MWY5OWFmMjY2OXAxODEwMDM@top-boar-81003.upstash.io:6379"

Write-Host "Setting Google Cloud Project to $ProjectID..."
gcloud config set project $ProjectID

Write-Host "Enabling required APIs (Cloud Run, Cloud Build, Artifact Registry)..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

Write-Host "Deploying to Cloud Run..."
gcloud run deploy vergil-dashboard `
    --source . `
    --region us-central1 `
    --allow-unauthenticated `
    --set-env-vars="REDIS_URL=$RedisUrl"

Write-Host "Deployment initiated. Check the output above for the public URL once it finishes."
