# MediCare DevOps Website

Responsive static healthcare demo website deployed with Docker, Jenkins, and Kubernetes Blue-Green routing.

## What's in the website
- Healthcare services, clinic information, and a responsive landing page.
- Appointment request preview that runs only in the browser; it does not submit or save personal data.
- Clear demo-only notice. This is not a real medical provider.
- Blue and Green versions with a visible deployment label.

## Build and deploy updated Blue/Green website images on the existing K3s EC2 host

After merging this change into `main`, SSH into the existing EC2 instance and run from a clean clone of the repository:

```bash
git clone https://github.com/Vamsi-Vyas/medicare-devops.git
cd medicare-devops
git pull origin main

# Build versioned images from the correct HTML source
docker build -f Dockerfile.blue -t medicare-devops:blue-v2 .
docker build -f Dockerfile.green -t medicare-devops:green-v2 .

# Import Docker images into the K3s containerd image store
docker save -o /tmp/medicare-blue-v2.tar medicare-devops:blue-v2
docker save -o /tmp/medicare-green-v2.tar medicare-devops:green-v2
sudo k3s ctr images import --namespace k8s.io /tmp/medicare-blue-v2.tar
sudo k3s ctr images import --namespace k8s.io /tmp/medicare-green-v2.tar

# Update existing deployments using their actual container names
BLUE_CONTAINER=$(kubectl get deployment medicare-blue -o jsonpath='{.spec.template.spec.containers[0].name}')
GREEN_CONTAINER=$(kubectl get deployment medicare-green -o jsonpath='{.spec.template.spec.containers[0].name}')
kubectl set image deployment/medicare-blue "$BLUE_CONTAINER=medicare-devops:blue-v2"
kubectl set image deployment/medicare-green "$GREEN_CONTAINER=medicare-devops:green-v2"
kubectl rollout status deployment/medicare-blue --timeout=120s
kubectl rollout status deployment/medicare-green --timeout=120s

# Route the website to Blue first
kubectl patch service medicare-service --type=merge -p '{"spec":{"selector":{"app":"medicare","version":"blue"}}}'
kubectl get service medicare-service
kubectl get endpoints medicare-service
curl -fsS http://127.0.0.1:30080/ | grep -E 'Thoughtful care|DEPLOYMENT'
```

To switch the website to Green:
```bash
kubectl patch service medicare-service --type=merge -p '{"spec":{"selector":{"app":"medicare","version":"green"}}}'
kubectl get endpoints medicare-service
curl -fsS http://127.0.0.1:30080/ | grep -E 'Thoughtful care|DEPLOYMENT'
```

If any command fails, stop and inspect `kubectl get deployments,pods,svc` and `kubectl describe deployment medicare-blue`; do not claim deployment success until the rollout and HTTP test pass. The commands above update the existing local K3s image store and deployments, not a public container registry.

## Classroom access
The current Service is expected to use NodePort 30080. Confirm it first:
```bash
kubectl get svc medicare-service
curl -I http://127.0.0.1:30080/
``
For your teacher to open the site from another network, the EC2 instance must have a public IP and the subnet route table must route to an Internet Gateway. In the EC2 security group, temporarily allow inbound TCP 30080 from the required classroom IPs (or, for a short classroom demo of this static site only, from `0.0.0.0/0`). Do not open SSH to the internet; keep port 22 restricted to your own current IP. Remove the broad 30080 rule after the demo if it is no longer needed.

Example URL, if the current EC2 public IP is still correct:
`http://98.93.100.162:30080`

A public URL is not verified until it loads from a browser outside the EC2 instance. If it times out, verify the security group, network ACL, public subnet route, service endpoints, and NodePort listener.

## Jenkins
The existing Jenkinsfile validates the source, runs Trivy checks, builds a smoke-test image, verifies Kubernetes rollout, and switches Service traffic. It currently does not build/import these versioned Blue/Green images into K3s automatically; the deployment commands above are a separate manual refresh step. Do not describe this image refresh as fully automated until the pipeline is updated and tested to perform it.
