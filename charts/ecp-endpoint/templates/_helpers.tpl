{{/* All entry points, including the ConfigMap renderer, validate instances here. */}}
{{- define "ecp-endpoint.instanceName" -}}
{{- $root := .root -}}
{{- $names := dict -}}
{{- $resources := dict -}}
{{- range $i := $root.Values.instance -}}
	{{- $n := required "instance.name is required" $i.name -}}
	{{- if or (gt (len $n) 63) (not (regexMatch "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$" $n)) -}}{{ fail "instance.name must be a DNS label (max 63)" }}{{- end -}}
	{{- if hasKey $names $n -}}{{ fail (printf "duplicate instance.name: %s" $n) }}{{- end -}}
	{{- $_ := set $names $n true -}}
	{{- if hasKey $i "fullnameOverride" -}}
		{{- if or (gt (len $i.fullnameOverride) 45) (not (regexMatch "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$" $i.fullnameOverride)) -}}{{ fail "instance.fullnameOverride must be a DNS label (1-45 characters)" }}{{- end -}}
	{{- end -}}
	{{- $base := default (printf "%s-%s-%s" $root.Release.Name $root.Chart.Name $n) $i.fullnameOverride -}}
	{{- if gt (len $base) 45 -}}{{- $base = printf "%s-%s" (trunc 34 $base | trimSuffix "-") (sha256sum $base | trunc 10) -}}{{- end -}}
	{{- if hasKey $resources $base -}}{{ fail (printf "duplicate instance resource name: %s" $base) }}{{- end -}}
	{{- $_ := set $resources $base true -}}
	{{- if or (not (hasKey $i "enabled")) $i.enabled -}}
		{{- $secret := required (printf "%s: existingSecret is required" $n) $i.existingSecret -}}
		{{- if or (gt (len $secret) 253) (not (regexMatch "^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$" $secret)) -}}{{ fail "existingSecret must be a DNS subdomain" }}{{- end -}}
		{{- $image := $i.image | default dict -}}
		{{- $_ := required "image.name is required" $image.name -}}
		{{- if hasKey $image "registry" -}}{{ fail "image.registry is unsupported; use the full repository in image.name" }}{{- end -}}
		{{- if not $image.digest -}}{{- $_ := required "image.tag or image.digest is required" $image.tag -}}{{- end -}}
		{{- $replicas := dig "replicaCount" 1 $i -}}
		{{- if not (regexMatch "^[0-9]+$" (toString $replicas)) -}}{{ fail "replicaCount must be a non-negative integer" }}{{- end -}}
		{{- if (dig "databaseWait" "enabled" false $i) -}}{{ fail "databaseWait is unsupported; database initialization is managed by the application" }}{{- end -}}
		{{- if gt (int $replicas) 1 -}}
			{{- $p := $i.ecpProperties | default dict -}}
			{{- if not (has "ecp-ha" (splitList "," (replace " " "" (default "" $p.springProfilesActive)))) -}}{{ fail "replicas > 1 require springProfilesActive including ecp-ha" }}{{- end -}}
			{{- $_ := required "HA requires an external database springDatasourceDriverClassName" $p.springDatasourceDriverClassName -}}
			{{- if not (has $p.springDatasourceDriverClassName (list "org.postgresql.Driver" "org.mariadb.jdbc.Driver" "com.mysql.jdbc.Driver" "com.mysql.cj.jdbc.Driver" "com.microsoft.sqlserver.jdbc.SQLServerDriver" "oracle.jdbc.OracleDriver" "oracle.jdbc.driver.OracleDriver")) -}}{{ fail "HA requires a supported external database springDatasourceDriverClassName" }}{{- end -}}
			{{- if not (regexMatch "^jdbc:(postgresql|mariadb|mysql|sqlserver|oracle):" (default "" $p.ecpDBUrl)) -}}{{ fail "HA requires an external database ecpDBUrl" }}{{- end -}}
		{{- end -}}
		{{- $svc := $i.service | default dict -}}
		{{- if not (or (dig "https" "port" 0 $svc) (dig "http" "port" 0 $svc)) -}}{{ fail "service requires an http.port or https.port listener" }}{{- end -}}
		{{- $ing := $i.ingress | default dict -}}
		{{- if and $ing.apiVersion (ne $ing.apiVersion "networking.k8s.io/v1") -}}{{ fail "ingress.apiVersion must be networking.k8s.io/v1" }}{{- end -}}
		{{- if $ing.enabled -}}{{- $_ := required "ingress.host is required" $ing.host -}}{{- end -}}
	{{- end -}}
{{- end -}}
{{- $base := default (printf "%s-%s-%s" $root.Release.Name $root.Chart.Name .instance.name) .instance.fullnameOverride -}}
{{- if gt (len $base) 45 -}}{{ printf "%s-%s" (trunc 34 $base | trimSuffix "-") (sha256sum $base | trunc 10) }}{{- else -}}{{ $base }}{{- end -}}
{{- end -}}

{{- define "ecp-endpoint.image" -}}
{{- if .digest -}}{{ printf "%s@%s" .name .digest }}{{- else -}}{{ printf "%s:%s" .name .tag }}{{- end -}}
{{- end -}}

{{- define "ecp-endpoint.busybox" -}}
{{- $image := dig "global" "imageBusybox" (dict) (merge (dict) .Values) -}}
{{- $name := default "busybox" $image.name -}}
{{- if regexMatch "(:[^/]+$|@)" $name -}}{{ $name }}{{- else -}}{{ printf "%s:%s" $name (default "1.37.0" $image.tag) }}{{- end -}}
{{- end -}}

{{- define "ecp-endpoint.probes" -}}
{{- $result := dict -}}
{{- range $kind := list "startupProbe" "readinessProbe" "livenessProbe" -}}
{{- $defaults := dict "enabled" (ne $kind "livenessProbe") "initialDelaySeconds" 0 "periodSeconds" 10 "timeoutSeconds" 2 "failureThreshold" 3 "successThreshold" 1 -}}
{{- if eq $kind "startupProbe" -}}{{- $_ := set $defaults "failureThreshold" 60 -}}{{- end -}}
{{- $p := mergeOverwrite $defaults (deepCopy (get $.instance $kind | default dict)) -}}
{{- if $p.enabled -}}
{{- $probe := pick $p "initialDelaySeconds" "periodSeconds" "timeoutSeconds" "failureThreshold" "successThreshold" -}}
{{- $_ := set $probe "tcpSocket" (dict "port" $.port) -}}
{{- $_ := set $result $kind $probe -}}
{{- end -}}
{{- end -}}
{{- if $result -}}{{ toYaml $result }}{{- end -}}
{{- end -}}

{{- define "ecp-endpoint.claim" -}}
{{- $spec := dict "accessModes" (list "ReadWriteOnce") "resources" (dict "requests" (dict "storage" .size)) -}}
{{- $class := dig "global" "storage" "class" "" (merge (dict) .root.Values) -}}
{{- if $class -}}{{- $_ := set $spec "storageClassName" (ternary "" $class (eq $class "-")) -}}{{- end -}}
{{- list (dict "metadata" (dict "name" .name) "spec" $spec) | toYaml -}}
{{- end -}}

{{- define "ecp-endpoint.publicConfig" -}}
{{- $values := deepCopy .root.Values -}}
{{- $_ := set $values "instance" (list .instance) -}}
{{- $context := dict "Values" $values "Release" .root.Release "Chart" .root.Chart "Capabilities" .root.Capabilities "Files" .root.Files "Template" .root.Template -}}
{{- $config := include "ecp-endpoint.configuration" $context | fromYaml -}}
{{- if hasKey $config "Error" -}}{{ fail "invalid rendered configuration" }}{{- end -}}
{{- omit $config.data "ecp.properties" "ecp-users.properties" "ecp-password.properties" "jmxremote.password" "jmxremote.ssl" "server.xml" "users.properties" | toYaml -}}
{{- end -}}
{{/* End of chart-local helpers. */}}

