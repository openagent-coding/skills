# Pipeline Authoring Reference

## Table of Contents
- [Pipeline Definition](#pipeline-definition)
- [Pipeline Return Values](#pipeline-return-values)
- [Wiring Components](#wiring-components)
- [Conditions](#conditions)
- [Loops](#loops)
- [Exit Handlers](#exit-handlers)
- [Sub-pipelines](#sub-pipelines)
- [Importer](#importer)
- [Placeholders](#placeholders)
- [Compilation](#compilation)
- [Local Execution](#local-execution)
- [KFP CLI](#kfp-cli)

## Pipeline Definition

```python
from kfp import dsl, compiler

@dsl.pipeline(
    name='my-pipeline',
    description='Pipeline description',
    pipeline_root='s3://bucket/pipeline-root',
)
def my_pipeline(
    param_a: str = 'default',
    param_b: int = 10,
    param_c: float = 0.5,
    param_d: bool = True,
    param_e: list = [1, 2, 3],
    param_f: dict = {'key': 'value'},
):
    task1 = component_a(input=param_a)
    task2 = component_b(data=task1.output)
```

Pipeline parameters must be typed and should have defaults. Supported types: `str`, `int`, `float`, `bool`, `list`, `dict`.

### PipelineConfig

Configure pipeline-level behavior:

```python
config = dsl.PipelineConfig(
    workspace=dsl.WorkspaceConfig(size='50Gi'),   # shared PVC for all tasks
    ttl_seconds_after_finished=3600,               # cleanup workflow after 1 hour
    ttl_seconds_after_failure=86400,               # keep failed workflows for 24 hours
    ttl_seconds_after_success=1800,                # keep successes for 30 minutes
    active_deadline_seconds=7200,                   # kill pipeline after 2 hours
)

@dsl.pipeline(pipeline_config=config)
def my_pipeline():
    ...
```

| Parameter | Purpose |
|---|---|
| `workspace` | Shared PVC across all tasks (see [rhoai-patterns.md > Workspace PVC](rhoai-patterns.md#workspace-pvc)) |
| `ttl_seconds_after_finished` | Delete workflow resource N seconds after completion |
| `ttl_seconds_after_success` | Override TTL for successful runs |
| `ttl_seconds_after_failure` | Override TTL for failed runs |
| `active_deadline_seconds` | Max runtime before forced termination |

## Pipeline Return Values

Pipelines can return outputs, enabling composable sub-pipelines:

```python
@dsl.pipeline
def training_pipeline(data: str) -> str:
    preprocess_task = preprocess(data=data)
    train_task = train(dataset=preprocess_task.output)
    return train_task.output  # exposed as pipeline output

# Consume as sub-pipeline
@dsl.pipeline
def outer_pipeline():
    result = training_pipeline(data='gs://bucket/data')
    deploy(model=result.output)
```

Return values can be `task.output` (single output) or `task.outputs['name']` (named output).

## Wiring Components

```python
@dsl.pipeline
def my_pipeline(text: str):
    # Pipeline param -> component
    t1 = comp_a(text=text)

    # Single output -> next component
    t2 = comp_b(data=t1.output)

    # Named outputs -> next component
    t3 = comp_c(
        accuracy=t2.outputs['accuracy'],
        model=t2.outputs['model'],
    )

    # Explicit ordering without data dependency
    t4 = comp_d(flag=True).after(t3)
```

Rules:
- `task.output` -- single return value
- `task.outputs['name']` -- named return (NamedTuple) or artifact output
- Data dependencies create implicit ordering
- `.after()` only needed for ordering without data flow

## Conditions

### If / Elif / Else

```python
@dsl.pipeline
def my_pipeline():
    coin = flip_coin()

    with dsl.If(coin.output == 'heads'):
        t1 = print_and_return(text='heads!')

    with dsl.Elif(coin.output == 'tails'):
        t2 = print_and_return(text='tails!')

    with dsl.Else():
        t3 = print_and_return(text='edge!')

    # Consume output from whichever branch ran
    result = dsl.OneOf(t1.output, t2.output, t3.output)
    final = use_result(text=result)
```

`dsl.Condition` is deprecated -- use `dsl.If` instead.

### OneOf Requirements
- Requires an `dsl.Else` branch
- All branches must produce outputs of the same type
- Used to pass conditional results to downstream tasks

### Nested Conditions

```python
with dsl.If(task1.output == 'a'):
    with dsl.If(task2.output > 5):
        inner_task = process(mode='a-high')
    with dsl.Else():
        inner_task = process(mode='a-low')
with dsl.Else():
    outer_else = process(mode='b')
```

## Loops

### Static List

```python
with dsl.ParallelFor(['item1', 'item2', 'item3']) as item:
    task = process(text=item)
```

### Dict Items (structured loop variables)

```python
items = [{'name': 'alice', 'age': 30}, {'name': 'bob', 'age': 25}]
with dsl.ParallelFor(items=items) as item:
    task = greet(name=item.name, age=item.age)
```

### Dynamic Output (from upstream task)

```python
@dsl.component
def generate_items() -> list:
    return [{'name': 'alice'}, {'name': 'bob'}]

@dsl.pipeline
def my_pipeline():
    gen = generate_items()
    with dsl.ParallelFor(gen.output) as item:
        process(name=item.name)
```

### Parallelism Control

```python
with dsl.ParallelFor(items=my_list, parallelism=2) as item:
    task = process(item=item)
# parallelism=0 means unlimited (default)
```

### Collecting Loop Outputs

```python
with dsl.ParallelFor([1, 2, 3]) as num:
    t = double(num=num)

# Collect all outputs into a list
aggregator = sum_all(numbers=dsl.Collected(t.output))

# For artifacts:
with dsl.ParallelFor(items) as item:
    t = train(data=item)
merge = merge_models(models=dsl.Collected(t.outputs['model']))
```

### Nested Loops

```python
with dsl.ParallelFor(['a', 'b']) as outer:
    with dsl.ParallelFor([1, 2, 3]) as inner:
        task = process(letter=outer, number=inner)
```

**Gotcha:** Parameters from nested loops produce multilevel nested lists. Artifacts are collected in a flat list.

### Loops with Conditions

```python
with dsl.ParallelFor(items) as item:
    with dsl.If(item.category == 'train'):
        train_task = train_model(data=item.path)
    with dsl.Else():
        eval_task = evaluate(data=item.path)
```

## Exit Handlers

Run cleanup/notification logic regardless of pipeline success or failure.

```python
@dsl.component
def cleanup(status: dsl.PipelineTaskFinalStatus):
    print(f'Pipeline state: {status.state}')        # SUCCEEDED, FAILED, CANCELLED
    print(f'Error code: {status.error_code}')
    print(f'Error message: {status.error_message}')
    print(f'Pipeline name: {status.pipeline_task_name}')
    print(f'Resource name: {status.pipeline_job_resource_name}')

@dsl.pipeline
def my_pipeline():
    exit_task = cleanup()
    with dsl.ExitHandler(exit_task, name='pipeline-cleanup'):
        t1 = step_one()
        t2 = step_two(data=t1.output)
```

### Conditional Exit Handler (sub-pipeline as exit task)

```python
@dsl.pipeline
def exit_handler_pipeline(status: dsl.PipelineTaskFinalStatus):
    state = get_state(status=status)
    with dsl.If(state.output == 'FAILED'):
        send_notification(msg='Pipeline failed!')

@dsl.pipeline
def my_pipeline():
    exit_task = exit_handler_pipeline()
    with dsl.ExitHandler(exit_task):
        train()
```

### ignore_upstream_failure

```python
t1 = might_fail()
t2 = cleanup(result=t1.output).ignore_upstream_failure()
```

**Requirement:** All inputs consumed from an upstream task must have default values.

## Sub-pipelines

Pipelines can be used as components inside other pipelines:

```python
@dsl.pipeline
def training_subpipeline(data: str) -> str:
    t1 = preprocess(data=data)
    t2 = train(processed=t1.output)
    return t2.output

@dsl.pipeline
def main_pipeline(dataset_uri: str):
    download_task = download_data(uri=dataset_uri)
    model = training_subpipeline(data=download_task.output)
    deploy(model=model.output)
```

## Importer

Import pre-existing artifacts into the pipeline:

```python
@dsl.pipeline
def my_pipeline(model_uri: str = 'gs://bucket/model'):
    imported = dsl.importer(
        artifact_uri=model_uri,
        artifact_class=dsl.Model,
        reimport=False,
        metadata={'framework': 'pytorch', 'version': '2.0'},
    )
    evaluate(model=imported.output)
```

- `reimport=True` -- always re-import even if URI matches cached artifact
- `artifact_uri` can be a static string or pipeline parameter
- Supports `oci://` URIs (KFP 2.5+)

## Placeholders

System-provided runtime values:

```python
dsl.PIPELINE_JOB_NAME_PLACEHOLDER            # Pipeline run display name
dsl.PIPELINE_JOB_ID_PLACEHOLDER              # Pipeline run UUID
dsl.PIPELINE_JOB_RESOURCE_NAME_PLACEHOLDER   # Full resource path
dsl.PIPELINE_TASK_NAME_PLACEHOLDER           # Current task name
dsl.PIPELINE_TASK_ID_PLACEHOLDER             # Current task UUID
dsl.PIPELINE_ROOT_PLACEHOLDER               # Pipeline root storage path
dsl.PIPELINE_JOB_CREATE_TIME_UTC_PLACEHOLDER
dsl.PIPELINE_JOB_SCHEDULE_TIME_UTC_PLACEHOLDER
```

Usage:
```python
@dsl.pipeline
def my_pipeline():
    register(
        run_id=dsl.PIPELINE_JOB_ID_PLACEHOLDER,
        run_name=dsl.PIPELINE_JOB_NAME_PLACEHOLDER,
    )
```

## Compilation

```python
from kfp import compiler

compiler.Compiler().compile(
    pipeline_func=my_pipeline,
    package_path='pipeline.yaml',
)
```

### Options

```python
compiler.Compiler().compile(
    pipeline_func=my_pipeline,
    package_path='pipeline.yaml',
    pipeline_name='override-name',
    pipeline_parameters={'param_a': 'override_default'},
    type_check=True,
)
```

### Compile Guard (always include)

```python
if __name__ == '__main__':
    compiler.Compiler().compile(
        pipeline_func=my_pipeline,
        package_path=__file__.replace('.py', '.yaml'),
    )
```

### Kubernetes Native API Mode (KFP 2.14+)

```python
from kfp.compiler.compiler_utils import KubernetesManifestOptions

compiler.Compiler().compile(
    pipeline_func=my_pipeline,
    package_path='pipeline-k8s.yaml',
    kubernetes_manifest_format=True,
    kubernetes_manifest_options=KubernetesManifestOptions(
        pipeline_name='my-pipeline',
        namespace='my-namespace',
        include_pipeline_manifest=True,
    ),
)
```

### Individual Component Compilation

Components can be compiled standalone:
```python
compiler.Compiler().compile(my_component, package_path='component.yaml')
```

## Local Execution

Test components locally without deploying to a cluster. Requires `kfp.local`.

```python
from kfp import local

# SubprocessRunner -- lightweight, runs in subprocess (Python components only)
local.init(runner=local.SubprocessRunner(use_venv=True))

# DockerRunner -- runs in Docker containers (all component types)
local.init(runner=local.DockerRunner())
```

Once initialized, call components directly as Python functions:

```python
@dsl.component(packages_to_install=['pandas'])
def process(data: str) -> str:
    import pandas as pd
    return data.upper()

# Runs locally -- returns the actual output
result = process(data='hello')
```

### Limitations

- No support for `dsl.If`, `dsl.ParallelFor`, `dsl.ExitHandler` (control flow)
- No caching, retry, or resource management
- No cloud authentication forwarding
- `SubprocessRunner` only supports lightweight Python components

### Configuration

```python
local.init(
    runner=local.SubprocessRunner(use_venv=True),
    pipeline_root='./local_outputs',    # where artifacts are stored
    raise_on_error=True,                # raise exceptions on failure
)
```

## KFP CLI

Common CLI commands for pipeline development:

```bash
# Compile pipeline
kfp dsl compile --py pipeline.py --output pipeline.yaml
kfp dsl compile --py pipeline.py --function my_pipeline --pipeline-parameters '{"key": "value"}'

# Build containerized component
kfp component build src/ --component-filepattern my_component.py --push-image

# Pipeline management
kfp pipeline create --pipeline-name my-pipeline pipeline.yaml
kfp pipeline list
kfp pipeline create-version --pipeline-name my-pipeline --version v2 pipeline-v2.yaml

# Run management
kfp run create --pipeline-name my-pipeline --experiment-name my-exp
kfp run list
kfp run get <run-id>

# Experiment management
kfp experiment create my-experiment
kfp experiment list
```
