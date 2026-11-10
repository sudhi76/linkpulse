{{- define "linkpulse.fullname" -}}
{{- if contains .Chart.Name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "linkpulse.api.name" -}}
{{- printf "%s-api" (include "linkpulse.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "linkpulse.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
app.kubernetes.io/part-of: linkpulse
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/* Selector labels must never change after the first install. */}}
{{- define "linkpulse.api.selectorLabels" -}}
app.kubernetes.io/name: linkpulse
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: api
{{- end -}}

{{- define "linkpulse.api.labels" -}}
{{ include "linkpulse.labels" . }}
{{ include "linkpulse.api.selectorLabels" . }}
app.kubernetes.io/version: {{ .Values.api.image.tag | trunc 63 | quote }}
{{- end -}}
