# Gotchas and Common Pitfalls

Quick checklist of non-obvious behaviors. Each links to the canonical documentation.

## Component Authoring

- **Hermetic functions**: Lightweight `@dsl.component` functions cannot reference anything outside their body -- imports, constants, helpers must be inside. Use `additional_funcs` for shared helpers. See [component-authoring.md > Hermetic Constraint](component-authoring.md#hermetic-constraint).

- **`packages_to_install` is slow**: Runtime pip adds 30-120s per task. Use containerized components (`target_image`) for production. See [component-authoring.md > Containerized Python Components](component-authoring.md#containerized-python-components).

- **`pip_index_urls` drops pypi.org**: When specifying custom PyPI URLs, KFP does NOT include `https://pypi.org/simple` automatically -- you must add it explicitly. See [component-authoring.md > Decorator Parameters](component-authoring.md#decorator-parameters).

- **Use traditional artifact syntax on RHOAI**: `Input[Dataset]`, `Output[Model]` -- not the Pythonic return-based syntax (Vertex AI only). See [component-authoring.md > Artifact I/O Syntax](component-authoring.md#artifact-io-syntax-use-this-for-kfp-open-source--rhoai).

- **Container component output serialization**: Container components must manually write output as JSON to the system-provided path. Python components handle this automatically. See [component-authoring.md > Container Components](component-authoring.md#container-components).

## Pipeline Authoring

- **`dsl.Condition` is deprecated**: Use `dsl.If` / `dsl.Elif` / `dsl.Else`. The new API supports `dsl.OneOf`. See [pipeline-authoring.md > Conditions](pipeline-authoring.md#conditions).

- **`dsl.OneOf` requires `dsl.Else`**: The compiler mandates an Else branch when using OneOf. All branches must produce same-type outputs. See [pipeline-authoring.md > OneOf Requirements](pipeline-authoring.md#oneof-requirements).

- **Nested ParallelFor output shapes**: Parameters from nested loops produce multilevel nested lists, but artifacts are collected flat. See [pipeline-authoring.md > Nested Loops](pipeline-authoring.md#nested-loops).

- **`ignore_upstream_failure` requires defaults**: All inputs consumed from an upstream task must have default values in the component definition. See [pipeline-authoring.md > ignore_upstream_failure](pipeline-authoring.md#ignore_upstream_failure).

- **`.after()` vs data dependencies**: If task B uses task A's output, ordering is implicit -- `.after()` is only needed for ordering without data flow. See [pipeline-authoring.md > Wiring Components](pipeline-authoring.md#wiring-components).

## Task Configuration

- **Caching env var timing**: `KFP_DISABLE_EXECUTION_CACHING_BY_DEFAULT` must be set BEFORE importing kfp. See [task-configuration.md > Caching](task-configuration.md#caching).

- **Disable caching for non-deterministic tasks**: Data downloads, training, and evaluation should always use `task.set_caching_options(False)`. See [task-configuration.md > Caching](task-configuration.md#caching).

## Kubernetes

- **Security context overrides**: Admin-set defaults (`allowPrivilegeEscalation=false`, drop ALL capabilities, `seccompProfile=RuntimeDefault`) cannot be overridden by the SDK. See [kubernetes-features.md > Security Context](kubernetes-features.md#security-context).

## Platform

- **Pipeline root required for artifacts**: Without proper object storage (S3, GCS, SeaweedFS), artifact-producing components will fail. On RHOAI, configured at the Data Science Pipelines level.

- **Workspace requires KFP 2.15.0+**: `dsl.PipelineConfig(workspace=...)` is an upstream KFP SDK feature (not RHOAI-specific) requiring KFP 2.15.0+. Kubernetes manifest compilation requires KFP 2.14.0+.
