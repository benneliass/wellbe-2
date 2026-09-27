{{- define "wellbe-local.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "wellbe-local.labels" -}}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{/*
Canonical Postgres connection. Every consumer (migration jobs AND app
deployments) MUST source the DB credential from these helpers so the
user/password/host/db can never diverge into conflicting literals
(e.g. "wellbe" vs "wellbe_dev"). Single source of truth: .Values.postgres.*
*/}}
{{- define "wellbe-local.pgHost" -}}
wellbe-postgres:5432
{{- end }}

{{- define "wellbe-local.databaseUrl" -}}
postgresql://{{ .Values.postgres.user }}:{{ .Values.postgres.password }}@{{ include "wellbe-local.pgHost" . }}/{{ .Values.postgres.database }}
{{- end }}

{{- define "wellbe-local.databaseUrlAsync" -}}
postgresql+asyncpg://{{ .Values.postgres.user }}:{{ .Values.postgres.password }}@{{ include "wellbe-local.pgHost" . }}/{{ .Values.postgres.database }}
{{- end }}

{{/*
Canonical Redis URL. Single source of truth so no consumer hardcodes a
divergent host/port. Source: redis-service name + .Values.redis.port.
*/}}
{{- define "wellbe-local.redisUrl" -}}
redis://wellbe-redis:{{ .Values.redis.port }}/0
{{- end }}

{{/*
Shared pod scheduling block. Emits imagePullSecrets and nodeSelector from
values so every pod spec (deployments, statefulset, jobs) can pin scheduling
and registry auth from a single source of truth. When the values are empty
(the kind/local default) this renders nothing, keeping local behavior intact.
Used by remote targets (e.g. the k3s homeserver) to pull from ghcr and keep
all workloads off a specific node.
*/}}
{{- define "wellbe-local.podScheduling" -}}
{{- with .Values.imagePullSecrets }}
imagePullSecrets:
{{ toYaml . | trim | indent 2 }}
{{- end }}
{{- with .Values.scheduling.nodeSelector }}
nodeSelector:
{{ toYaml . | trim | indent 2 }}
{{- end }}
{{- end }}

{{/*
Container resources block. Pass a component's `resources` map; renders nothing
when it is empty (the kind/local default), so local behavior is unchanged.
Remote targets set requests/limits so WellBe cannot starve a shared node.
*/}}
{{- define "wellbe-local.resources" -}}
{{- with . }}
resources:
{{ toYaml . | trim | indent 2 }}
{{- end }}
{{- end }}

{{/*
ArgoCD sync wave for staged startup on shared clusters. ArgoCD applies each
wave and waits for it to become healthy before starting the next, so data
stores come up before the services that depend on them. Plain Helm ignores it.
*/}}
{{- define "wellbe-local.syncWave" -}}
argocd.argoproj.io/sync-wave: {{ . | quote }}
{{- end }}
