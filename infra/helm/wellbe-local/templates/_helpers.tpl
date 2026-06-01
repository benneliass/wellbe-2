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
