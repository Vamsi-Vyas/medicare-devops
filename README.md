# medicare-devops

MediCare DevOps demonstration project for Jenkins CI/CD, Docker, Kubernetes Blue-Green deployment, and Trivy-based security scanning.

## Optional dashboard
An additional browser dashboard is being developed in the `feature/medicare-devops-dashboard` branch. See [dashboard/README.md](dashboard/README.md) for intended installation and secure SSH-tunnel access. Do not expose dashboard port 5000 directly to the internet.

## Existing project
- `app/`: MediCare demo page.
- `Dockerfile`: unprivileged NGINX image.
- `Jenkinsfile`: pipeline for validation, Trivy scans, Docker build/smoke test, Kubernetes readiness, and Blue-Green service switching.

Dashboard code is separate from the current deployment and has not been installed on EC2.