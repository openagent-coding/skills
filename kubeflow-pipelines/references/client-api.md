# KFP Client API Reference

## Table of Contents
- [Initialization](#initialization)
- [Submitting Runs](#submitting-runs)
- [Pipeline Management](#pipeline-management)
- [Experiment Management](#experiment-management)
- [Run Management](#run-management)
- [Recurring Runs](#recurring-runs)

## Initialization

```python
from kfp.client import Client

# Inside cluster
client = Client(host='http://ml-pipeline-ui:80')

# Outside cluster (port-forwarded)
client = Client(host='http://localhost:3000')

# With authentication
client = Client(
    host='https://kfp.example.com',
    existing_token='my-token',
    namespace='my-namespace',
    ssl_ca_cert='/path/to/ca.crt',
)

# Multi-user Kubeflow Platform
client = Client()  # uses KF_PIPELINES_SA_TOKEN_PATH env var
```

Constructor parameters:
- `host` -- KFP API endpoint
- `namespace` -- Kubernetes namespace (default: `kubeflow`)
- `existing_token` -- pre-obtained auth token
- `cookies` -- auth cookies
- `proxy` -- HTTP proxy
- `ssl_ca_cert` -- CA certificate path
- `kube_context` -- kubectl context name
- `credentials` -- custom credential provider (TokenCredentialsBase)
- `verify_ssl` -- verify SSL certificates

## Submitting Runs

### From Pipeline Function (most common)

```python
run = client.create_run_from_pipeline_func(
    pipeline_func=my_pipeline,
    arguments={'param_a': 'value', 'param_b': 42},
    run_name='my-run-2024',
    experiment_name='my-experiment',
    namespace='my-namespace',
    pipeline_root='s3://bucket/root',
    enable_caching=True,
    service_account='pipeline-runner',
)
```

### From Compiled YAML

```python
run = client.create_run_from_pipeline_package(
    pipeline_file='pipeline.yaml',
    arguments={'param_a': 'value'},
    run_name='my-run',
    experiment_name='my-experiment',
)
```

### Lower-Level Run

```python
run = client.run_pipeline(
    experiment_id='exp-123',
    job_name='my-run',
    pipeline_package_path='pipeline.yaml',
    params={'param_a': 'value'},
    pipeline_root='s3://bucket/root',
    enable_caching=True,
)
```

## Pipeline Management

```python
# Upload compiled pipeline
pipeline = client.upload_pipeline(
    pipeline_package_path='pipeline.yaml',
    pipeline_name='my-pipeline',
    description='Pipeline description',
)

# Upload from function (compiles + uploads)
pipeline = client.upload_pipeline_from_pipeline_func(
    pipeline_func=my_pipeline,
    pipeline_name='my-pipeline',
)

# Upload new version
version = client.upload_pipeline_version(
    pipeline_package_path='pipeline-v2.yaml',
    pipeline_version_name='v2',
    pipeline_id=pipeline.pipeline_id,
)

# List, get, delete
pipelines = client.list_pipelines(page_size=20)
pipeline = client.get_pipeline(pipeline_id='...')
pipeline_id = client.get_pipeline_id(name='my-pipeline')
client.delete_pipeline(pipeline_id='...')
```

## Experiment Management

```python
exp = client.create_experiment(name='my-experiment', namespace='my-ns')
exp = client.get_experiment(experiment_name='my-experiment')
exps = client.list_experiments(page_size=20)
```

## Run Management

```python
run = client.get_run(run_id='...')
runs = client.list_runs(page_size=20, experiment_id='...')

# Wait for completion
completed_run = client.wait_for_run_completion(run_id='...', timeout=3600)

# Lifecycle
client.archive_run(run_id='...')
client.terminate_run(run_id='...')
client.delete_run(run_id='...')
```

## Recurring Runs

```python
recurring = client.create_recurring_run(
    experiment_id='exp-123',
    job_name='nightly-training',
    cron_expression='0 0 * * *',       # 6-field cron
    pipeline_package_path='pipeline.yaml',
    params={'data_date': '2024-01-01'},
    no_catchup=True,
    max_concurrency=1,
    enabled=True,
)
```

Alternatively use `interval_second` instead of `cron_expression`:
```python
recurring = client.create_recurring_run(
    experiment_id='exp-123',
    job_name='hourly-check',
    interval_second=3600,
    pipeline_package_path='pipeline.yaml',
)
```
