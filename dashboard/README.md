# MediCare DevOps Dashboard

Optional authenticated browser dashboard for the existing EC2 setup. It is intended to show real service and Kubernetes status, switch the existing Service selector between ready Blue/Green deployments, and display actual Trivy configuration scan output. It must not be exposed directly to the internet.

## Security
- Bind to EC2 loopback only and access through an SSH tunnel.
- Use authentication and keep SSH inbound restricted to your current public IP /32.
- Traffic switching changes the Service selector only; it does not build or publish an image.
- Scanner errors and missing project paths must be displayed as errors, never as clean results.

## Install
From the repository root on EC2:
```bash
chmod +x install-dashboard.sh
./install-dashboard.sh
```

Then on your local computer, open an SSH tunnel:
```bash
ssh -i "PATH_TO_YOUR_KEY.pem" -L 5000:127.0.0.1:5000 ec2-user@98.93.100.162
```
Keep the tunnel open and browse to http://127.0.0.1:5000. Use the dashboard credentials generated during installation.

Do not add port 5000 to the EC2 security group. If the EC2 public IP changes, use the current IP in the SSH command.

## Verify
```bash
sudo systemctl status medicare-dashboard --no-pager -l
sudo journalctl -u medicare-dashboard -n 80 --no-pager
```

The dashboard is an additional component; existing Jenkins, Docker, and K3s are not reinstalled by the installer.
