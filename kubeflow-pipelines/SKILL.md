---
name: kubeflow-pipelines
description: >
  Write Kubeflow Pipelines SDK v2 pipelines for OpenShift AI (RHOAI) / Data Science Pipelines.
  Covers component authoring (@dsl.component, @dsl.container_component, containerized components),
  pipeline composition (conditions, loops, exit handlers, sub-pipelines), Kubernetes configuration
  (secrets, PVCs, node selectors, tolerations, GPUs, resource limits), task configuration
  (caching, retry, env vars), compilation, and KFP client API.
  Use when: (1) writing new KFP v2 pipelines, (2) authoring pipeline components,
  (3) configuring Kubernetes resources for pipeline tasks, (4) compiling or submitting pipelines,
  (5) any question about kfp SDK v2 API, kfp.dsl, kfp.kubernetes, or kfp.compiler,
  (6) working with .py files that import kfp or contain @dsl.pipeline / @dsl.component decorators.
---

# Kubeflow Pipelines SDK v2

Write KFP v2 pipelines targeting OpenShift AI (RHOAI) Data Science Pipelines.

## Quick Start

Minimal pipeline skeleton:

```python
from kfp import dsl, compiler

@dsl.component(base_image='registry.access.redhat.com/ubi9/python-311:latest')
def greet(name: str) -> str:
    return f'Hello, {name}!'

@dsl.pipeline(name='hello-pipeline')
def hello_pipeline(name: str = 'world'):
    greet(name=name)

if __name__ == '__main__':
    compiler.Compiler().compile(
        pipeline_func=hello_pipeline,
        package_path=__file__.replace('.py', '.yaml'),
    )
```

## Workflow

1. **Define components** -- `@dsl.component` for Python, `@dsl.container_component` for arbitrary containers. See [references/component-authoring.md](references/component-authoring.md).
2. **Compose pipeline** -- Wire components with `@dsl.pipeline`, add control flow (If/Elif/Else, ParallelFor, ExitHandler). See [references/pipeline-authoring.md](references/pipeline-authoring.md).
3. **Configure tasks** -- Set resources, caching, retry, env vars. See [references/task-configuration.md](references/task-configuration.md).
4. **Add K8s features** -- Secrets, PVCs, node selectors, tolerations, GPUs via `kfp.kubernetes`. See [references/kubernetes-features.md](references/kubernetes-features.md).
5. **Compile** -- `compiler.Compiler().compile(pipeline_func, 'pipeline.yaml')`
6. **Submit** -- Via KFP client or RHOAI UI. See [references/client-api.md](references/client-api.md).

## Component Types Decision Tree

- **Pure Python logic, no special dependencies** -> `@dsl.component`
- **Python with pip packages (dev/prototyping)** -> `@dsl.component(packages_to_install=[...])`
- **Python with pip packages (production)** -> `@dsl.component(target_image='...')` (containerized)
- **Non-Python binary or custom entrypoint** -> `@dsl.container_component`
- **Jupyter notebook as a step** -> `@dsl.notebook_component(notebook_path='...')`
- **Pre-existing component YAML** -> `components.load_component_from_file('component.yaml')`

## Essential Rules

1. **Hermetic functions**: Lightweight `@dsl.component` functions cannot reference anything outside their body. All imports and constants must be inside the function.
2. **Use traditional artifact syntax**: `Input[Dataset]`, `Output[Model]` -- not the Pythonic return-based syntax (Vertex AI only).
3. **UBI base images on RHOAI**: Use `registry.access.redhat.com/ubi9/python-311:latest` instead of `python:3.11`.
4. **Always include compile guard**: `if __name__ == '__main__': compiler.Compiler().compile(...)`.
5. **Disable caching** for data downloads, training, and evaluation: `task.set_caching_options(False)`.
6. **Set resource requests AND limits** for production pipelines.
7. **Use `dsl.If`/`dsl.Elif`/`dsl.Else`** instead of deprecated `dsl.Condition`.
8. **Keyword arguments only** when calling components: `comp(epochs=100)` not `comp(100)`.

## RHOAI-Specific Patterns

For OpenShift AI patterns including workspace PVCs, multi-stage pipeline structure, parameter naming conventions, secret management, and GPU configuration, see [references/rhoai-patterns.md](references/rhoai-patterns.md).

## Common Pitfalls

See [references/gotchas.md](references/gotchas.md) for known issues including pip_index_urls behavior, OneOf requirements, nested loop output shapes, and caching env var timing.

## Reference Files

| File | When to read |
|---|---|
| [component-authoring.md](references/component-authoring.md) | Writing components, choosing component type, artifact types, Input vs InputPath, custom artifacts |
| [pipeline-authoring.md](references/pipeline-authoring.md) | Composing pipelines, control flow, compilation, local execution, CLI |
| [kubernetes-features.md](references/kubernetes-features.md) | Secrets, PVCs, node selectors, tolerations, security context |
| [task-configuration.md](references/task-configuration.md) | Resources, caching, retry, env vars, debug pause, type checking |
| [rhoai-patterns.md](references/rhoai-patterns.md) | RHOAI workspace PVC, multi-stage pipelines, GPU setup, secrets |
| [client-api.md](references/client-api.md) | Submitting runs, managing pipelines/experiments |
| [gotchas.md](references/gotchas.md) | Quick checklist of non-obvious behaviors with cross-references |
