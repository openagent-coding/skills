# RHOAI / OpenShift AI Patterns

Patterns specific to running KFP pipelines on Red Hat OpenShift AI (RHOAI) / Data Science Pipelines.

## Table of Contents
- [Base Images](#base-images)
- [Workspace PVC](#workspace-pvc)
- [Multi-Stage Pipeline Structure](#multi-stage-pipeline-structure)
- [Parameter Naming Convention](#parameter-naming-convention)
- [Secret Management](#secret-management)
- [GPU Configuration](#gpu-configuration)
- [Resource Limits](#resource-limits)
- [Component Library Structure](#component-library-structure)
- [Pipeline Provenance](#pipeline-provenance)
- [Metadata YAML](#metadata-yaml)

## Base Images

Use Red Hat UBI-based images instead of default `python:3.11`:

```python
@dsl.component(
    base_image='registry.access.redhat.com/ubi9/python-311:latest',
    packages_to_install=['pandas'],
)
def my_component(...):
    ...
```

Common RHOAI base images:
- `registry.access.redhat.com/ubi9/python-311:latest`
- `registry.access.redhat.com/ubi9/python-312:latest`
- `quay.io/modh/odh-generic-data-science-notebook:v3` (for notebook-based components)

## Workspace PVC

The upstream KFP SDK (2.15.0+) supports a shared workspace PVC at the pipeline level. All tasks automatically have access. This is commonly used on RHOAI.

```python
PVC_SIZE = "50Gi"
PVC_STORAGE_CLASS = "nfs-csi"
PVC_ACCESS_MODES = ["ReadWriteMany"]

@dsl.pipeline(
    name="training-pipeline",
    description="Fine-tuning pipeline with shared workspace",
    pipeline_config=dsl.PipelineConfig(
        workspace=dsl.WorkspaceConfig(
            size=PVC_SIZE,
            kubernetes=dsl.KubernetesWorkspaceConfig(
                pvcSpecPatch={
                    "accessModes": PVC_ACCESS_MODES,
                    "storageClassName": PVC_STORAGE_CLASS,
                }
            ),
        ),
    ),
)
def my_pipeline(...):
    # Tasks access workspace via placeholder
    download_task = download_data(
        pvc_mount_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
        ...
    )
    train_task = train_model(
        pvc_mount_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
        ...
    )
```

Prefer workspace PVC over manual `CreatePVC`/`DeletePVC` for shared storage on RHOAI.

Requires KFP 2.15.0+.

## Multi-Stage Pipeline Structure

RHOAI finetuning pipelines follow a consistent 4-stage pattern:

```python
@dsl.pipeline(name="sft-pipeline")
def sft_pipeline(
    # Phase 1: Dataset params
    phase_01_dataset_man_data_uri: str,
    phase_01_dataset_man_data_split: float = 0.9,
    # Phase 2: Training params
    phase_02_train_man_batch_size: int = 128,
    phase_02_train_opt_learning_rate: float = 1e-5,
    # Phase 3: Evaluation params
    phase_03_eval_opt_tasks: str = "arc_easy",
    # Phase 4: Registry params
    phase_04_registry_opt_model_name: str = "",
):
    # Stage 1: Dataset Download
    dataset_task = dataset_download(
        data_uri=phase_01_dataset_man_data_uri,
        split=phase_01_dataset_man_data_split,
        pvc_mount_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
    )

    # Stage 2: Training
    training_task = train_model(
        dataset=dataset_task.outputs["train_dataset"],
        batch_size=phase_02_train_man_batch_size,
        learning_rate=phase_02_train_opt_learning_rate,
    )

    # Stage 3: Evaluation
    eval_task = evaluate(
        model=training_task.outputs["output_model"],
        eval_dataset=dataset_task.outputs["eval_dataset"],
        tasks=phase_03_eval_opt_tasks,
    )

    # Stage 4: Model Registry
    registry_task = register_model(
        model=training_task.outputs["output_model"],
        metrics=training_task.outputs["output_metrics"],
        eval_results=eval_task.outputs["output_results"],
    )
```

## Parameter Naming Convention

For complex pipelines with many parameters, use structured naming:

```
phase_NN_category_req_paramname
```

| Segment | Meaning |
|---|---|
| `phase_NN` | Pipeline stage: `01`=dataset, `02`=training, `03`=eval, `04`=registry |
| `category` | Domain: `dataset`, `train`, `eval`, `registry` |
| `req` | Requirement level: `man`=mandatory (no default), `opt`=optional (has default) |
| `paramname` | Descriptive parameter name |

Examples:
```python
phase_01_dataset_man_data_uri: str,          # required dataset URI
phase_01_dataset_opt_data_split: float = 0.9, # optional split ratio
phase_02_train_man_batch_size: int,           # required batch size
phase_02_train_opt_cpu: str = "4",            # optional CPU request
phase_02_train_opt_memory: str = "64Gi",      # optional memory request
```

## Secret Management

For the `kubernetes.use_secret_as_env()` API, see [kubernetes-features.md > Secrets](kubernetes-features.md#secrets).

RHOAI pipelines commonly use these secrets:

| Secret | Env Vars | Optional? | Used By |
|---|---|---|---|
| `hf-token` | `HF_TOKEN` | Yes | download, train, eval |
| `s3-secret` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Yes | download |
| `kubernetes-credentials` | `KUBERNETES_SERVER_URL`, `KUBERNETES_AUTH_TOKEN` | No | model registry |

Apply shared secrets to multiple tasks in a loop:
```python
for task in [download_task, train_task, eval_task]:
    kubernetes.use_secret_as_env(task, secret_name='hf-token',
        secret_key_to_env={'HF_TOKEN': 'HF_TOKEN'}, optional=True)
```

## GPU Configuration

For resource and accelerator APIs, see [task-configuration.md > Resources](task-configuration.md#resources). For node selectors, see [kubernetes-features.md > Node Selectors](kubernetes-features.md#node-selectors).

RHOAI GPU setup combines all three -- resources, accelerator, and node selector:

```python
training_task.set_cpu_request('4').set_memory_request('32Gi')
training_task.set_cpu_limit('8').set_memory_limit('64Gi')
training_task.set_accelerator_type('nvidia.com/gpu')
training_task.set_accelerator_limit(1)
kubernetes.add_node_selector(training_task, 'nvidia.com/gpu.present', 'true')
```

## Resource Limits

Always set both requests and limits for production pipelines:

```python
task.set_cpu_request("2").set_memory_request("8Gi")
task.set_cpu_limit("32").set_memory_limit("64Gi")
```

## Component Library Structure

Organize reusable components in a shared library:

```
components/
    data_processing/
        dataset_download.py
    training/
        finetuning/
            sft.py
            lora.py
            osft.py
    evaluation/
        lm_eval.py
    deployment/
        kubeflow_model_registry.py
```

Import in pipelines:
```python
from components.data_processing.dataset_download import dataset_download
from components.training.finetuning.sft import train_model
from components.evaluation.lm_eval import universal_llm_evaluator
from components.deployment.kubeflow_model_registry import kubeflow_model_registry
```

Benefits:
- Same `dataset_download`, `evaluator`, and `model_registry` across SFT, LoRA, OSFT
- Only the training component changes per pipeline variant

## Pipeline Provenance

Track pipeline origin in model registry:

```python
registry_task = register_model(
    source_pipeline_name=PIPELINE_NAME,
    source_pipeline_run_id=dsl.PIPELINE_JOB_ID_PLACEHOLDER,
    source_pipeline_run_name=dsl.PIPELINE_JOB_NAME_PLACEHOLDER,
    source_namespace="",
)
```

## Metadata YAML

Each pipeline directory should include `metadata.yaml`:

```yaml
name: sft_pipeline
stability: alpha  # alpha, beta, stable
dependencies:
  kubeflow:
    - name: Pipelines
      version: '>=2.15.2'
  external_services:
    - name: HuggingFace Datasets
      version: ">=2.14.0"
    - name: Kubernetes
      version: ">=1.28.0"
tags:
  - training
  - fine_tuning
links:
  documentation: https://github.com/kubeflow/trainer
lastVerified: 2026-01-09T00:00:00Z
```
