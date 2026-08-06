# Deploying locally on Kubernetes

Free — runs on your machine. Requires a local cluster (Docker Desktop's
built-in Kubernetes, or `kind`/`minikube`) and `kubectl`.

```sh
# 1. build the two images (tags must match the manifests: *:local)
docker build -t money-split-web:local .
docker build -t money-split-frontend:local ./frontend

# kind only — Docker Desktop/minikube share the local image cache already:
# kind load docker-image money-split-web:local money-split-frontend:local

# 2. apply everything
kubectl apply -f k8s/

# 3. wait for pods to be ready
kubectl get pods --watch

# 4. reach the app
kubectl port-forward svc/frontend 8080:80
# open http://localhost:8080
```

To tear down: `kubectl delete -f k8s/`

## What's here
- `postgres` / `redis` — in-cluster, single replica, dev credentials in `00-secret.yaml`.
- `web` — Django + gunicorn; an initContainer runs migrations before it starts.
- `worker` — Celery worker, same image as `web`.
- `frontend` — React build served by nginx, proxies `/api` to the `web` Service.

## Not included (add if you actually need it)
- **Ingress / TLS** — using `port-forward` instead since that needs no ingress controller installed.
- **HPA / resource limits** — add `resources:` + `HorizontalPodAutoscaler` if you see real load.
- **Cloud deploy** — push images to a registry, point `image:` at them, swap Postgres/Redis for managed services, and put real secrets in a proper secret manager instead of `00-secret.yaml`.
