# Guidelines for new commands
# - Start with a verb
# - Keep it short (max. 3 words in a command)
# - Group commands by context. Include group name in the command name.
# - Mark things private that are util functions with [private] or _var
# - Don't over-engineer, keep it simple.
# - Don't break existing commands
# - Run just --fmt --unstable after adding new commands

set dotenv-load := true

# ---------------------------------------------------------------------------------------------------------------------
# Private vars

_red := '\033[1;31m'
_cyan := '\033[1;36m'
_green := '\033[1;32m'
_yellow := '\033[1;33m'
_nc := '\033[0m'

# ---------------------------------------------------------------------------------------------------------------------
# Aliases

alias rs := run-server
alias rc := run-client
alias rj := run-jupyter
alias b := build

# ---------------------------------------------------------------------------------------------------------------------

@default:
    just --list

# ---------------------------------------------------------------------------------------------------------------------

# Run a local syftbox server on port 5001
[group('server')]
run-server port="5001" uvicorn_args="":
    mkdir -p .server/data
    SYFTBOX_DATA_FOLDER=.server/data uv run uvicorn syftbox.server.server:app --reload --reload-dir ./syftbox --port {{ port }} {{ uvicorn_args }}

# ---------------------------------------------------------------------------------------------------------------------

# Run a local syftbox client on any available port between 8080-9000
[group('client')]
run-client name port="auto" server="http://localhost:5001":
    #!/bin/bash
    set -eou pipefail

    # generate a local email from name, but if it looks like an email, then use it as is
    EMAIL="{{ name }}@openmined.org"
    if [[ "{{ name }}" == *@*.* ]]; then EMAIL="{{ name }}"; fi

    # if port is auto, then generate a random port between 8000-8090, else use the provided port
    PORT="{{ port }}"
    if [[ "$PORT" == "auto" ]]; then PORT="0"; fi

    # Working directory for client is .clients/<email>
    DATA_DIR=.clients/$EMAIL
    mkdir -p $DATA_DIR

    echo -e "Email      : {{ _green }}$EMAIL{{ _nc }}"
    echo -e "Client     : {{ _cyan }}http://localhost:$PORT{{ _nc }}"
    echo -e "Server     : {{ _cyan }}{{ server }}{{ _nc }}"
    echo -e "Data Dir   : $DATA_DIR"

    uv run syftbox/client/cli.py --config=$DATA_DIR/config.json --data-dir=$DATA_DIR --email=$EMAIL --port=$PORT --server={{ server }} --no-open-dir

# ---------------------------------------------------------------------------------------------------------------------

[group('client')]
run-live-client server="https://syftbox.openmined.org/":
    uv run syftbox client --server={{ server }}

# ---------------------------------------------------------------------------------------------------------------------

# Run a local syftbox app command
[group('app')]
run-app name command subcommand="":
    #!/bin/bash
    set -eou pipefail

    # generate a local email from name, but if it looks like an email, then use it as is
    EMAIL="{{ name }}@openmined.org"
    if [[ "{{ name }}" == *@*.* ]]; then EMAIL="{{ name }}"; fi

    # Working directory for client is .clients/<email>
    DATA_DIR=$(pwd)/.clients/$EMAIL
    mkdir -p $DATA_DIR
    echo -e "Data Dir   : $DATA_DIR"

    uv run syftbox/main.py app {{ command }} {{ subcommand }} --config=$DATA_DIR/config.json

# ---------------------------------------------------------------------------------------------------------------------

# Build syftbox wheel
[group('build')]
build:
    rm -rf dist
    uv build


# Build syftbox wheel
[group('install')]
install:
    rm -rf dist
    uv build
    uv tool install $(ls ./dist/*.whl) --reinstall

# Bump version, commit and tag
[group('build')]
bump-version level="patch":
    #!/bin/bash
    # We need to uv.lock before we can commit the whole thing in the repo.
    # DO not bump the version on the uv.lock file, else other packages with same version might get updated

    set -eou pipefail

    # sync dev dependencies for bump2version
    uv sync --frozen

    # get the current and new version
    BUMPVERS_CHANGES=$(uv run bump2version --dry-run --allow-dirty --list {{ level }})
    CURRENT_VERSION=$(echo "$BUMPVERS_CHANGES" | grep current_version | cut -d'=' -f2)
    NEW_VERSION=$(echo "$BUMPVERS_CHANGES" | grep new_version | cut -d'=' -f2)
    echo "Bumping version from $CURRENT_VERSION to $NEW_VERSION"

    # first bump version
    uv run bump2version {{ level }}

    # update uv.lock file to reflect new package version
    uv lock

    # commit the changes
    git commit -am "Bump version $CURRENT_VERSION -> $NEW_VERSION"
    git tag -a $NEW_VERSION -m "Release $NEW_VERSION"

# ---------------------------------------------------------------------------------------------------------------------

[group('test')]
test-e2e-old test_name:
    @echo "Using SyftBox from {{ _green }}'$(which syftbox)'{{ _nc }}"
    chmod +x ./tests/e2e/{{ test_name }}/run.bash
    bash ./tests/e2e.old/{{ test_name }}/run.bash

[group('test')]
test-e2e test_name:
    #!/bin/sh
    uv sync --frozen
    . .venv/bin/activate
    echo "Using SyftBox from {{ _green }}'$(which syftbox)'{{ _nc }}"
    pytest -sq --color=yes ./tests/e2e/test_{{ test_name }}.py

# ---------------------------------------------------------------------------------------------------------------------

# Build & Deploy syftbox to a remote server using SSH
[group('deploy')]
upload-dev keyfile remote="user@0.0.0.0": build
    #!/bin/bash
    set -eou pipefail

    # there will be only one wheel file in the dist directory, but you never know...
    LOCAL_WHEEL=$(ls dist/*.whl | grep syftbox | head -n 1)

    # Remote paths to copy the wheel to
    REMOTE_DIR="~"
    REMOTE_WHEEL="$REMOTE_DIR/$(basename $LOCAL_WHEEL)"

    echo -e "Deploying {{ _cyan }}$LOCAL_WHEEL{{ _nc }} to {{ _green }}{{ remote }}:$REMOTE_WHEEL{{ _nc }}"

    # change permissions to comply with ssh/scp
    chmod 600 {{ keyfile }}

    # Use scp to transfer the file to the remote server
    scp -i {{ keyfile }} "$LOCAL_WHEEL" "{{ remote }}:$REMOTE_DIR"

    # install pip package
    ssh -i {{ keyfile }} {{ remote }} "uv venv && uv pip install $REMOTE_WHEEL"

    # restart service
    # NOTE - syftbox service is created manually on the remote server
    ssh -i {{ keyfile }} {{ remote }} "sudo systemctl daemon-reload && sudo systemctl restart syftbox"
    echo -e "{{ _green }}Deployed SyftBox local wheel to {{ remote }}{{ _nc }}"

# Deploy syftbox from pypi to a remote server using SSH
[group('deploy')]
upload-pip version keyfile remote="user@0.0.0.0":
    #!/bin/bash
    set -eou pipefail

    # change permissions to comply with ssh/scp
    chmod 600 {{ keyfile }}

    echo -e "Deploying syftbox version {{ version }} to {{ remote }}..."

    # install pip package
    ssh -i {{ keyfile }} {{ remote }} "uv venv && uv pip install syftbox=={{ version }}"

    # restart service
    ssh -i {{ keyfile }} {{ remote }} "sudo systemctl daemon-reload && sudo systemctl restart syftbox"

    echo -e "{{ _green }}Deployed SyftBox {{ version }} to {{ remote }}{{ _nc }}"

# ---------------------------------------------------------------------------------------------------------------------

[group('utils')]
ssh keyfile remote="user@0.0.0.0":
    ssh -i {{ keyfile }} {{ remote }}

# remove all local files & directories
[group('utils')]
reset:
    rm -rf ./.clients ./.server ./dist ./.e2e

[group('utils')]
run-jupyter jupyter_args="":
    uv run --frozen --with "jupyterlab" \
        jupyter lab {{ jupyter_args }}


# ---------------------------------------------------------------------------------------------------------------------
# SigNoz
# Reference: https://github.com/OpenMined/PySyft/blob/dev/justfile

_name_signoz := "signoz"
_ctx_signoz := "k3d-" + _name_signoz
port_signoz_ui := "3301"
port_signoz_otel := "4318"

otel_config_path := "custom-otel-collector-config.yaml"
signoz_otel_url := "http://host.k3d.internal:" + port_signoz_otel

[group('cluster')]
[private]
delete-cluster *args='':
    #!/bin/bash
    set -euo pipefail

    # remove the k3d- prefix
    ARGS=$(echo "{{ args }}" | sed -e 's/k3d-//g')
    k3d cluster delete $ARGS

# Launch SigNoz. UI=http://localhost:3301 OTEL=http://localhost:4318 (port_signoz_ui=3301 port_signoz_otel=4318)
[group('signoz')]
start-signoz: && (apply-signoz _ctx_signoz) (setup-signoz _ctx_signoz)
    k3d cluster create {{ _name_signoz }} \
        --port {{ port_signoz_ui }}:3301@loadbalancer \
        --port {{ port_signoz_otel }}:4318@loadbalancer \
        --k3s-arg "--disable=metrics-server@server:*"

# Remove SigNoz from the cluster
[group('signoz')]
delete-signoz: (delete-cluster _name_signoz)

# Remove all SigNoz data without deleting
[group('signoz')]
reset-signoz:
    @kubectl exec --context {{ _ctx_signoz }} -n platform chi-signoz-clickhouse-cluster-0-0-0 --container clickhouse -- \
        clickhouse-client --multiline --multiquery "\
        TRUNCATE TABLE signoz_analytics.rule_state_history_v0; \
        TRUNCATE TABLE signoz_logs.logs_v2; \
        TRUNCATE TABLE signoz_logs.logs; \
        TRUNCATE TABLE signoz_logs.usage; \
        TRUNCATE TABLE signoz_metrics.usage; \
        TRUNCATE TABLE signoz_traces.durationSort; \
        TRUNCATE TABLE signoz_traces.signoz_error_index_v2; \
        TRUNCATE TABLE signoz_traces.signoz_index_v2; \
        TRUNCATE TABLE signoz_traces.signoz_spans; \
        TRUNCATE TABLE signoz_traces.top_level_operations; \
        TRUNCATE TABLE signoz_traces.usage_explorer; \
        TRUNCATE TABLE signoz_traces.usage;"

    @echo "Done. Traces & logs are cleared, but graphs may still show old content."

# K9s into the Signoz cluster
[group('signoz')]
k9s-signoz:
    k9s --context {{ _ctx_signoz }}

[group('signoz')]
[private]
apply-signoz kube_context:
    @echo "Installing SigNoz in kube context {{ kube_context }}"
    helm install signoz signoz \
        --repo https://charts.signoz.io \
        --kube-context {{ kube_context }} \
        --namespace platform \
        --create-namespace \
        --version 0.58.0 \
        --set frontend.service.type=LoadBalancer \
        --set otelCollector.service.type=LoadBalancer \
        --set otelCollectorMetrics.service.type=LoadBalancer

[group('signoz')]
[private]
setup-signoz kube_context:
    #!/bin/bash
    set -euo pipefail

    SIGNOZ_URL="http://localhost:3301"
    USERNAME="admin@localhost"
    PASSWORD="password"
    DASHBOARDS=(
        https://raw.githubusercontent.com/SigNoz/dashboards/refs/heads/main/hostmetrics/hostmetrics.json,
    )

    echo "Waiting for SigNoz frontend to be available..."
    bash ./wait_for.sh service signoz-frontend \
        --namespace platform --context {{ kube_context }} &> /dev/null

    echo "Setting up SigNoz account..."
    curl -s --retry 5 --retry-all-errors -X POST \
        -H "Content-Type: application/json" \
        --data "{\"email\":\"$USERNAME\",\"name\":\"admin\",\"orgName\":\"openmined\",\"password\":\"$PASSWORD\"}" \
        "$SIGNOZ_URL/api/v1/register"

    echo "Adding some dashboards..."
    AUTH_TOKEN=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
        "$SIGNOZ_URL/api/v1/login" | jq -r .accessJwt)

    if [ -z "$AUTH_TOKEN" ] || [ "$AUTH_TOKEN" = "null" ]; then
        echo "Could not set up dashboards. But you can do it manually from the dashboard."
        exit 0
    fi

    for URL in "${DASHBOARDS[@]}"; do
        curl -s -X POST \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $AUTH_TOKEN" \
            -d "$(curl -s --retry 3 --retry-all-errors "$URL")" \
            "$SIGNOZ_URL/api/v1/dashboards" &> /dev/null
    done

    printf "\nSignoz is ready and running on %s\n" "$SIGNOZ_URL"
    printf "Email: \033[1;36m%s\033[0m\n" "$USERNAME"
    printf "Password: \033[1;36m%s\033[0m\n" "$PASSWORD"

[group('signoz')]
install-otel-collector:
    #!/bin/bash
    sudo apt-get update
    sudo apt-get -y install wget
    wget https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.115.1/otelcol-contrib_0.115.1_linux_amd64.deb
    sudo dpkg -i otelcol-contrib_0.115.1_linux_amd64.deb

[group('signoz')]
run-otel-collector:
    otelcol-contrib --config {{ otel_config_path }}
