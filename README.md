# LinkPulse

LinkPulse is a URL shortener with real-time click analytics. It runs as three Python services on Kubernetes and is delivered through GitOps on AWS EKS, with infrastructure managed in Terraform.

> **Status:** under active development. See [Roadmap](#roadmap) for what is in progress.

## Features

- Create short links with optional custom aliases and expiry
- Fast redirects: click tracking happens asynchronously and never slows the redirect down
- Per-link analytics: total clicks, clicks over time, referrers and countries
- REST API alongside the web interface

## Architecture

```
                          ┌──────────────┐
           users ───────► │   Ingress    │  (ALB on AWS, ingress-nginx locally)
                          └──────┬───────┘
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
          ┌────────────┐                  ┌────────────┐
          │    web     │ ───── REST ────► │    api     │
          └────────────┘                  └─────┬──────┘
                                      reads/    │    click events
                                      writes    │    (LPUSH)
                               ┌────────────────┴───────┐
                               ▼                        ▼
                        ┌────────────┐           ┌────────────┐
                        │ PostgreSQL │ ◄──────── │   Redis    │
                        └────────────┘  worker   └────────────┘
                               ▲        aggregates     │
                               └──── ┌────────────┐ ◄──┘
                                     │   worker   │
                                     └────────────┘
```

| Service | Responsibility |
|---|---|
| `web` | Server-rendered UI for creating links and viewing stats |
| `api` | Link management, redirects (`GET /{code}`), stats endpoints |
| `worker` | Consumes click events from Redis and writes aggregated stats to PostgreSQL |

**Why a queue for clicks:** the redirect is the latency-critical path. The API records the click with a single Redis push and returns the redirect immediately; aggregation happens in the worker, which can fall behind under load and catch up without affecting users.

## Delivery pipeline

```
 push / PR ──► GitHub Actions ──► lint, test ──► build image ──► Trivy scan ──► push to registry
                                                                                    │
                                                         image tag bump (PR) ◄──────┘
                                                                │
                                                                ▼
                                                  deploy/ (Helm values per env)
                                                                │
                                                     Argo CD sync + Argo Rollouts
                                                                │
                                                     canary 20% → 50% → 100%
                                                     auto-rollback on failed analysis
```

- Every change reaches production through a pull request; there is no `kubectl apply` by hand.
- Images are tagged with the commit SHA and are immutable.
- GitHub Actions authenticates to AWS with OIDC; no long-lived access keys exist.

## Platform

| Area | Tooling |
|---|---|
| Runtime | Kubernetes: AWS EKS (production), kind (local) |
| Infrastructure as code | Terraform: VPC, EKS, ECR, IAM (IRSA), S3 remote state |
| CI | GitHub Actions, Ruff, pytest, Trivy, SBOM generation |
| CD | Argo CD (app-of-apps), Helm, Argo Rollouts |
| Metrics and alerting | Prometheus, Alertmanager, Grafana |
| Logs and traces | Loki, OpenTelemetry, Tempo |
| Policy and secrets | Kyverno, External Secrets Operator with AWS Secrets Manager |
| Networking | AWS Load Balancer Controller, Kubernetes NetworkPolicies |
| Autoscaling | HorizontalPodAutoscaler, Karpenter |

## Reliability targets

| SLO | Target |
|---|---|
| Redirect availability | 99.9% of `GET /{code}` requests succeed, over 30 days |
| Redirect latency | 99.5% of redirects complete in under 300 ms |
| Analytics freshness | Click stats are no more than 60 s behind |

Alerts fire on error-budget burn rate rather than on individual errors.

## Repository layout

```
services/
  api/          FastAPI service
  web/          FastAPI + Jinja UI
  worker/       click event consumer
deploy/
  charts/       Helm chart for the application
  envs/         per-environment values (dev, prod)
  argocd/       Argo CD applications (app-of-apps)
infra/
  terraform/    AWS infrastructure
platform/       cluster add-ons: monitoring, policies, secrets, ingress
docs/
  runbooks/     on-call procedures per alert
  adr/          architecture decision records
.github/
  workflows/    CI pipelines
```

## Local development

Requirements: Docker, Python 3.12+, and for the Kubernetes setup: kind, kubectl, Helm.

```bash
# Run the full stack with Docker Compose
docker compose up --build

# Run tests for a service
cd services/api && pytest
```

Before pushing, run the same checks CI runs on every pull request (from `services/api`):

```bash
ruff check . && ruff format --check . && pytest --cov=app --cov-fail-under=80
```

A local Kubernetes environment that mirrors production (kind + Argo CD + monitoring) is created with `make cluster-up`.

## Roadmap

**Application**
- [ ] `api`, `web` and `worker` services with unit and integration tests
- [ ] Container images: multi-stage builds, non-root, minimal base
- [ ] Docker Compose stack for local development
- [ ] Health, readiness and Prometheus metrics endpoints

**Continuous integration**
- [x] Lint, test and coverage on every pull request
- [x] Image build and push tagged by commit SHA
- [x] Vulnerability scanning with Trivy; SBOM per image

**Kubernetes and delivery**
- [x] Helm chart with probes, resource limits and HPA
- [ ] Argo CD app-of-apps with `dev` and `prod` environments
- [ ] Automated image tag promotion via pull request
- [ ] Canary releases with Argo Rollouts and automated rollback

**Observability**
- [ ] RED metrics per service, queue depth and worker lag
- [ ] Grafana dashboards and alert rules as code
- [ ] Centralised logs (Loki) and distributed tracing (OpenTelemetry, Tempo)
- [ ] SLO burn-rate alerts

**Security**
- [ ] Kyverno admission policies (no `:latest`, required limits, non-root)
- [ ] Secrets from AWS Secrets Manager via External Secrets
- [ ] NetworkPolicies and least-privilege RBAC

**AWS infrastructure**
- [ ] Terraform: VPC, EKS, ECR, IAM roles for service accounts, remote state
- [ ] GitHub Actions to AWS via OIDC
- [ ] AWS Load Balancer Controller and Karpenter

**Operations**
- [ ] Load testing with k6
- [ ] Runbooks for every alert
- [ ] PostgreSQL backup and restore procedure
- [ ] Failure-injection testing and incident write-ups

## License

[MIT](LICENSE)
