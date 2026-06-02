# Task Configuration Reference

All `PipelineTask` methods return `self` for chaining.

## Table of Contents
- [Resources](#resources)
- [Caching](#caching)
- [Retry](#retry)
- [Environment Variables](#environment-variables)
- [Display Name](#display-name)
- [Debug Pause](#debug-pause)
- [Ordering and Upstream Failure](#ordering-and-upstream-failure)
- [Container Image Override](#container-image-override)
- [Type Checking](#type-checking)

## Resources

### CPU

```python
task.set_cpu_request('500m')  # millicores
task.set_cpu_limit('2')       # whole cores
```

### Memory

```python
task.set_memory_request('512Mi')
task.set_memory_limit('4Gi')
```

Suffixes: `E`, `Ei`, `P`, `Pi`, `T`, `Ti`, `G`, `Gi`, `M`, `Mi`, `K`, `Ki`

### GPU / Accelerators

```python
task.set_accelerator_type('nvidia.com/gpu')
task.set_accelerator_limit(1)
```

### Chained Example

```python
task = train_model(data=data_task.output)
task.set_cpu_request('4').set_cpu_limit('8')
task.set_memory_request('16Gi').set_memory_limit('32Gi')
task.set_accelerator_type('nvidia.com/gpu').set_accelerator_limit(2)
```

## Caching

```python
task.set_caching_options(enable_caching=False)
task.set_caching_options(enable_caching=True, cache_key='custom-key')
```

Caching is **enabled by default**. Disable for:
- Data downloads (content may change)
- Training (non-deterministic with GPU)
- Evaluation (should always re-run)

Override at submission:
```python
client.create_run_from_pipeline_func(pipeline, enable_caching=False)
```

Global disable via env var (must be set BEFORE importing kfp):
```python
import os
os.environ['KFP_DISABLE_EXECUTION_CACHING_BY_DEFAULT'] = 'true'
import kfp
```

## Retry

```python
task.set_retry(
    num_retries=3,
    backoff_duration='30s',     # initial wait (default '0s')
    backoff_factor=2.0,         # exponential factor (default 2.0)
    backoff_max_duration='3600s',  # max wait (default '3600s')
)
```

With 3 retries, `backoff_duration='30s'`, `backoff_factor=2.0`:
- Retry 1: wait 30s
- Retry 2: wait 60s
- Retry 3: wait 120s

## Environment Variables

```python
task.set_env_variable('MY_VAR', 'value')
task.set_env_variable('CUDA_VISIBLE_DEVICES', '0,1')
```

For secrets/configmaps as env vars, use `kubernetes.use_secret_as_env()` or `kubernetes.use_config_map_as_env()`.

## Display Name

```python
task.set_display_name('Step 1: Download Dataset')
```

## Debug Pause

Keep the pod alive after execution for `kubectl exec` debugging. Requires Argo Workflows 3.5+.

```python
task.set_debug_pause(
    before=False,    # pause before main process (inspect environment)
    after=True,      # pause after completion (default)
    on_error=False,  # only pause on failure
)

# Debug a failing training task:
train_task.set_debug_pause(after=True, on_error=True)
# Then: kubectl exec -it <pod-name> -- /bin/bash
```

## Ordering and Upstream Failure

See [pipeline-authoring.md > Wiring Components](pipeline-authoring.md#wiring-components) for task ordering (`.after()`, implicit data dependencies) and [pipeline-authoring.md > ignore_upstream_failure](pipeline-authoring.md#ignore_upstream_failure) for handling upstream failures.

## Container Image Override

```python
task.set_container_image('quay.io/my-org/custom-image:v2')
```

Takes precedence over `base_image` in `@dsl.component`. Supports dynamic values (pipeline parameters).

## Type Checking

The compiler enforces type checking at compile time:
- **Parameters**: Strict type match between producer output and consumer input
- **Artifacts**: `Artifact` is a wildcard -- compatible with any artifact subtype (Model, Dataset, etc.)
- **Disable globally**: `kfp.TYPE_CHECK = False` (use with caution)

```python
import kfp
kfp.TYPE_CHECK = False  # disable all compile-time type checking

# Artifact wildcard -- accepts any artifact type:
@dsl.component
def generic_logger(artifact: Input[Artifact]):  # accepts Model, Dataset, etc.
    print(artifact.uri)
```
