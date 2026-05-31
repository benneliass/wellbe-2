# Tiltfile — live dev loop for wellbe-2
# Syncs Python source changes into running Kind pods without rebuilding images.
# Prerequisites: tilt, kind (cluster: kind-desktop), helm, docker

allow_k8s_contexts('kind-desktop')

# ---------------------------------------------------------------------------
# Helm chart
# ---------------------------------------------------------------------------

k8s_yaml(helm(
    'infra/helm/wellbe-local',
    name='wellbe-local',
    namespace='wellbe',
))

# ---------------------------------------------------------------------------
# vault-writer
# ---------------------------------------------------------------------------

docker_build(
    'wellbe-vault-writer:local',
    context='.',
    dockerfile='backend/apps/vault-writer/Dockerfile',
    build_args={'DEV': 'true'},
    live_update=[
        sync(
            'backend/apps/vault-writer/src/',
            '/app/apps/vault-writer/src/',
        ),
        sync(
            'backend/packages/',
            '/app/packages/',
        ),
        # uvicorn --reload handles .py changes automatically;
        # restart the container when package files change so the
        # reloader picks them up from the updated source tree.
        run(
            'touch /tmp/reload-trigger',
            trigger=[
                'backend/apps/vault-writer/src/',
                'backend/packages/',
            ],
        ),
    ],
    only=[
        'backend/pyproject.toml',
        'backend/apps/vault-writer/',
        'backend/packages/',
    ],
    ignore=[
        '**/__pycache__',
        '**/*.pyc',
        '**/*.pyo',
        '**/*.egg-info',
    ],
)

k8s_resource(
    'vault-writer',
    port_forwards=['8002:8002'],
    labels=['app'],
)

# ---------------------------------------------------------------------------
# ingestion-worker
# ---------------------------------------------------------------------------

docker_build(
    'wellbe-ingestion-worker:local',
    context='.',
    dockerfile='backend/apps/ingestion-worker/Dockerfile',
    build_args={'DEV': 'true'},
    live_update=[
        sync(
            'backend/apps/ingestion-worker/src/',
            '/app/apps/ingestion-worker/src/',
        ),
        sync(
            'backend/packages/',
            '/app/packages/',
        ),
        run(
            'touch /tmp/reload-trigger',
            trigger=[
                'backend/apps/ingestion-worker/src/',
                'backend/packages/',
            ],
        ),
    ],
    only=[
        'backend/pyproject.toml',
        'backend/apps/ingestion-worker/',
        'backend/packages/',
    ],
    ignore=[
        '**/__pycache__',
        '**/*.pyc',
        '**/*.pyo',
        '**/*.egg-info',
    ],
)

k8s_resource(
    'ingestion-worker',
    port_forwards=['8003:8003'],
    labels=['app'],
)

# ---------------------------------------------------------------------------
# processing-worker
# ---------------------------------------------------------------------------

docker_build(
    'wellbe-processing-worker:local',
    context='.',
    dockerfile='backend/apps/processing-worker/Dockerfile',
    build_args={'DEV': 'true'},
    live_update=[
        sync(
            'backend/apps/processing-worker/src/',
            '/app/apps/processing-worker/src/',
        ),
        sync(
            'backend/packages/',
            '/app/packages/',
        ),
        run(
            'touch /tmp/reload-trigger',
            trigger=[
                'backend/apps/processing-worker/src/',
                'backend/packages/',
            ],
        ),
    ],
    only=[
        'backend/pyproject.toml',
        'backend/apps/processing-worker/',
        'backend/packages/',
    ],
    ignore=[
        '**/__pycache__',
        '**/*.pyc',
        '**/*.pyo',
        '**/*.egg-info',
    ],
)

k8s_resource(
    'processing-worker',
    port_forwards=['8004:8004'],
    labels=['app'],
)
