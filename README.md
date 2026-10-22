# Student Placement Readiness Tracker

**CCA 2 project:** CI/CD Pipeline Implementation and Deployment using Jenkins, Docker, and Kubernetes.

A responsive Flask + SQLite dashboard for maintaining student placement readiness. It includes a student directory, CGPA-based eligibility (CGPA >= 7.0), placement status tracking, search/filter, CSV export, automated tests, and a health endpoint for Kubernetes probes.

## Project structure

```text
placement-readiness-tracker-cca2/
├── app.py
├── templates/index.html
├── static/style.css
├── tests/test_app.py
├── requirements.txt
├── Dockerfile
├── Jenkinsfile
└── k8s/{deployment.yaml,service.yaml}
```

## Run locally (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. Health check: `http://127.0.0.1:5000/health`.

Run tests:

```powershell
pytest -q
```

## Run with Docker

```powershell
docker build -t placement-readiness-tracker:local .
docker run --rm -p 5000:5000 -e DATABASE_PATH=/tmp/students.db placement-readiness-tracker:local
```

## GitHub and Docker Hub setup

1. Create a GitHub repository and push this project.
2. Create a public Docker Hub repository named `placement-readiness-tracker` (or change `IMAGE_NAME` in the Jenkinsfile).
3. In Jenkins, add a **Username with password** credential with ID `dockerhub-credentials`; username is your Docker Hub username and password should be a Docker Hub access token.
4. Configure a Jenkins agent that has Python 3, Docker CLI/daemon access, `kubectl`, and access to the intended Kubernetes cluster.
5. Configure Minikube and kubectl on that agent, and verify `kubectl get nodes` works as the Jenkins service account. A Minikube cluster running only on a separate laptop is not automatically accessible from a remote Jenkins server.
6. In Jenkins, create a Pipeline job connected to your GitHub repository and use the repository `Jenkinsfile`.

> The included pipeline assumes a Linux Jenkins agent and that the agent already has working Docker and Kubernetes access. Configure those tools and cluster permissions before the first run. Do not hardcode registry credentials in source code.

## Kubernetes deployment

The Jenkins pipeline builds a versioned image, pushes it to Docker Hub, applies the Kubernetes Service and Deployment, updates the Deployment image to the build number, and waits for rollout completion.

The manifests use a placeholder image name; the pipeline replaces it with the image that was just pushed. For manual deployment, edit `k8s/deployment.yaml` and replace `DOCKERHUB_USERNAME` with your Docker Hub username, then run:

```powershell
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/placement-readiness-tracker
kubectl get pods,services
minikube service placement-readiness-tracker
```

For a Jenkins-managed Minikube cluster, run the commands on the same agent/host that owns the cluster. The sample uses an `emptyDir` volume so its SQLite data is temporary and may be lost if the Pod is recreated; that is acceptable for a CI/CD demo, but use a PersistentVolumeClaim for durable deployment data.

## Demonstrate the required CI/CD flow

1. Commit and push the project to GitHub.
2. Run the Jenkins pipeline and capture successful checkout, test, Docker build/push, deployment and rollout stages.
3. Open the application through the Minikube service and capture the dashboard.
4. Change a visible heading in `templates/index.html` (for example, change `Placement Readiness Tracker` to `Placement Readiness Tracker — v2`). Commit and push.
5. Run Jenkins again. Confirm a new build number/image is deployed and capture the updated page.
6. Include your GitHub URL, screenshots, Jenkinsfile, Dockerfile, Kubernetes YAML and a short explanation in your final report.

## Notes

- The eligibility threshold of 7.0 is a configurable demo rule, not an official placement policy.
- This is an educational demo, not a production system. It has no authentication or authorization; do not enter confidential student information.
- For a clean demo database, stop the app and remove the local `students.db` file.
