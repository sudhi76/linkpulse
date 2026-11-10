# LinkPulse

A URL shortener with click analytics, built and run the way a production platform team would do it: containers, CI/CD, Kubernetes, GitOps, observability, security, and AWS infrastructure as code.

The app is deliberately small. The point of this project is the **platform around it**.

## The app

| Service | What it does | Tech |
|---|---|---|
| `web` | Page to create short links and see click stats | Python (FastAPI + Jinja templates) |
| `api` | `POST /links`, `GET /{code}` redirect, `GET /links/{code}/stats` | Python (FastAPI), PostgreSQL |
| `worker` | Reads click events from a queue and aggregates stats | Python, Redis |

Each click on a short link: `api` redirects the user immediately and pushes a click event to Redis; `worker` consumes it and updates the stats in PostgreSQL. This gives us a database, a queue, a background job and user-facing latency, which are the things worth monitoring and scaling.

## Architecture (final state)

```
 Developer ──push──► GitHub (app code)
                        │
                        ▼
               GitHub Actions CI
     lint → test → build → Trivy scan → push image (GHCR/ECR)
                        │  bumps image tag
                        ▼
               GitOps repo (Helm values)
                        │  watched by
                        ▼
                     Argo CD ──► Kubernetes (kind locally, EKS on AWS)
                                   ├─ web / api / worker (Argo Rollouts canary)
                                   ├─ PostgreSQL, Redis
                                   ├─ ingress-nginx / AWS Load Balancer Controller
                                   ├─ Prometheus, Grafana, Loki, Tempo (OpenTelemetry)
                                   ├─ Kyverno policies, External Secrets
                                   └─ Karpenter node autoscaling (EKS)
                        ▲
     Terraform: VPC, EKS, ECR, IAM (IRSA), S3 state, GitHub OIDC
```

## Roadmap

Each phase ends with something working that you can demo, plus a short write-up in `docs/journal/`.

### Phase 0: Tools and foundations (local)
- [ ] Install Colima (Docker runtime), docker CLI, kind, kubectl, helm, k9s, terraform, awscli, argocd CLI
- [ ] Git basics: branches, PRs, conventional commits

### Phase 1: The app in containers
- [ ] Write the three services with unit tests (pytest)
- [ ] Multi-stage Dockerfiles, non-root user, small images
- [ ] `docker compose up` runs the whole app with Postgres and Redis
- [ ] `/healthz` and `/readyz` endpoints, `/metrics` (Prometheus client)

### Phase 2: CI with GitHub Actions
- [ ] Lint (ruff), tests, coverage on every PR
- [ ] Build and push images to GitHub Container Registry, tagged with the commit SHA
- [ ] Trivy image scan, fail on CRITICAL
- [ ] Generate an SBOM; cache dependencies to keep CI fast

### Phase 3: Kubernetes locally
- [ ] kind cluster with ingress-nginx
- [ ] Helm chart for the app: Deployments, Services, Ingress, ConfigMaps, Secrets
- [ ] Liveness/readiness probes, resource requests/limits, HPA
- [ ] PostgreSQL and Redis via Helm charts

### Phase 4: GitOps with Argo CD
- [ ] Install Argo CD, "app of apps" pattern
- [ ] `dev` and `prod` environments with separate Helm values
- [ ] CI opens a PR to bump the image tag; merging it deploys
- [ ] Argo Rollouts canary release with automatic rollback

### Phase 5: Observability
- [ ] kube-prometheus-stack: Prometheus, Alertmanager, Grafana
- [ ] App metrics: request rate, errors, latency (RED), queue depth, clicks/sec
- [ ] Grafana dashboards as code; alerts to Slack/email
- [ ] Logs with Loki, traces with OpenTelemetry + Tempo
- [ ] One SLO: 99.5% of redirects under 300 ms, with an error-budget alert

### Phase 6: Security
- [ ] Kyverno policies: no `:latest`, limits required, non-root containers
- [ ] External Secrets Operator (AWS Secrets Manager in phase 7)
- [ ] NetworkPolicies between services; least-privilege RBAC

### Phase 7: AWS with Terraform
- [ ] Remote state in S3 with locking
- [ ] VPC, EKS, ECR, IAM roles for service accounts (IRSA)
- [ ] GitHub Actions → AWS via OIDC (no stored access keys)
- [ ] AWS Load Balancer Controller, Karpenter, External Secrets with Secrets Manager
- [ ] Same Argo CD setup deploys to EKS
- [ ] `terraform destroy` after each session; a cost note in the README

### Phase 8: Operating it
- [ ] Load test with k6 and watch HPA/Karpenter scale
- [ ] Break things on purpose (kill pods, fill the queue, bad deploy) and write runbooks
- [ ] One written postmortem
- [ ] Postgres backup and restore drill

## Open-source contributions along the way

| Phase | Where I can contribute |
|---|---|
| 4 | Argo CD, Argo Rollouts |
| 5 | prometheus-community/helm-charts, OpenTelemetry |
| 6 | Kyverno, External Secrets Operator, Trivy |
| 7 | terraform-aws-modules, Karpenter, AWS Load Balancer Controller |

## Running costs

Phases 0–6 run free on a laptop. Phase 7 uses AWS: an EKS cluster with two small nodes costs roughly $3–5 for a few hours of practice. Always run `terraform destroy` when done.
