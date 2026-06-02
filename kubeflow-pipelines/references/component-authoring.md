# Component Authoring Reference

## Table of Contents
- [Lightweight Python Components](#lightweight-python-components)
- [Container Components](#container-components)
- [Containerized Python Components](#containerized-python-components)
- [Notebook Components](#notebook-components)
- [Loading Components from YAML](#loading-components-from-yaml)
- [Supported Types](#supported-types)
- [Artifact Types](#artifact-types)
- [Input vs InputPath](#input-vs-inputpath)
- [Custom Artifact Types](#custom-artifact-types)
- [Runtime Helpers](#runtime-helpers)

## Lightweight Python Components

The most common component type. Function must be **hermetic** -- no references to symbols defined outside the function body.

```python
@dsl.component
def add(a: int, b: int) -> int:
    return a + b
```

### Decorator Parameters

```python
@dsl.component(
    base_image='registry.access.redhat.com/ubi9/python-311:latest',
    packages_to_install=['pandas==2.0', 'scikit-learn'],
    pip_index_urls=['https://pypi.org/simple', 'https://custom.pypi.org/simple'],
    pip_trusted_hosts=['custom.pypi.org'],
    install_kfp_package=True,
    target_image=None,
    additional_funcs=[helper_fn],
)
def my_component(...):
    ...
```

| Parameter | Default | Purpose |
|---|---|---|
| `base_image` | `python:3.11` | Container image for execution |
| `packages_to_install` | `None` | Runtime pip install (slow -- prefer containerized for prod) |
| `pip_index_urls` | `None` | Custom PyPI indexes. **Must include `https://pypi.org/simple` explicitly** |
| `pip_trusted_hosts` | `None` | Hosts to skip TLS verification |
| `install_kfp_package` | `True` | Auto-installs kfp in container |
| `target_image` | `None` | Set to build a containerized Python component |
| `additional_funcs` | `None` | Helper functions to serialize alongside main function |
| `use_venv` | `False` | Execute in virtual environment |

### Hermetic Constraint

All imports, constants, and helper functions must be inside the function body:

```python
# CORRECT
@dsl.component
def process(data: str) -> str:
    import json
    THRESHOLD = 0.5
    parsed = json.loads(data)
    return json.dumps({k: v for k, v in parsed.items() if v > THRESHOLD})

# WRONG -- NameError at runtime
import json
THRESHOLD = 0.5

@dsl.component
def process(data: str) -> str:
    parsed = json.loads(data)  # fails
    return json.dumps({k: v for k, v in parsed.items() if v > THRESHOLD})
```

Exception: use `additional_funcs` to include helpers:
```python
def helper(x):
    return x * 2

@dsl.component(additional_funcs=[helper])
def my_comp(val: int) -> int:
    return helper(val)
```

### Single vs Multiple Returns

**Single return:**
```python
@dsl.component
def add(a: int, b: int) -> int:
    return a + b

# Access: task.output
```

**Multiple returns (NamedTuple):**
```python
from typing import NamedTuple

@dsl.component
def train(epochs: int) -> NamedTuple('Outputs', [('accuracy', float), ('model', Model)]):
    from collections import namedtuple
    output = namedtuple('Outputs', ['accuracy', 'model'])
    return output(0.95, trained_model)

# Access: task.outputs['accuracy'], task.outputs['model']
```

## Container Components

Full control over image, command, and args. Not limited to Python.

```python
@dsl.container_component
def train_model(
    data_path: dsl.InputPath(str),
    model_path: dsl.OutputPath(str),
    epochs: int,
):
    return dsl.ContainerSpec(
        image='registry.access.redhat.com/ubi9/python-311:latest',
        command=['python', '/app/train.py'],
        args=[
            '--data', data_path,
            '--output', model_path,
            '--epochs', epochs,
        ],
    )
```

Rules:
- Output parameters use `dsl.OutputPath(type)` -- system provides the path
- Output artifacts use `dsl.Output[ArtifactType]` -- access `.path` and `.uri`
- Never provide output parameters when calling the component
- Must write output as JSON to the system-provided path

### Placeholders in Container Components

```python
@dsl.container_component
def with_placeholders(name: Optional[str] = None):
    return dsl.ContainerSpec(
        image='alpine',
        command=['sh', '-c'],
        args=[
            dsl.IfPresentPlaceholder(
                input_name='name',
                then=['--name', name],
                else_=['--name', 'default'],
            ),
            dsl.ConcatPlaceholder(['prefix-', name, '-suffix']),
        ],
    )
```

## Containerized Python Components

Relaxes the hermetic constraint. Dependencies baked into image at build time.

```python
@dsl.component(
    base_image='registry.access.redhat.com/ubi9/python-311:latest',
    target_image='quay.io/my-org/my-component:v1',
)
def train_model(dataset: Input[Dataset], model: Output[Model]):
    from my_project.training import Trainer
    trainer = Trainer()
    trainer.train(dataset.path)
    trainer.save(model.path)
```

Build: `kfp component build src/ --component-filepattern my_component.py --push-image`

Prefer containerized components when:
- Using `packages_to_install` (runtime pip is slow)
- Need cross-module imports
- Production workloads requiring reproducibility

## Notebook Components

Run Jupyter notebooks as pipeline steps. Parameters are injected via Papermill (tag a cell `parameters`).

```python
@dsl.notebook_component(
    notebook_path='./train.ipynb',
    base_image='registry.access.redhat.com/ubi9/python-311:latest',
    packages_to_install=['papermill'],
)
def train_nb(epochs: int, lr: float, model: Output[Model]):
    dsl.run_notebook(epochs=epochs, lr=lr)
```

Accepts the same options as `@dsl.component` (base_image, packages_to_install, pip_index_urls, etc.) plus `notebook_path`.

## Loading Components from YAML

```python
from kfp import components

comp = components.load_component_from_file('component.yaml')
comp = components.load_component_from_url('https://raw.githubusercontent.com/.../component.yaml')
comp = components.load_component_from_text(yaml_string)
```

## Supported Types

### Parameter Types

| Python Type | KFP Type | Notes |
|---|---|---|
| `str` | string | |
| `int` | number | |
| `float` | number | |
| `bool` | boolean | |
| `list` | object | JSON-serialized |
| `dict` | object | JSON-serialized |
| `Optional[T]` | T or null | Must have default value |

All parameters are serialized as JSON under the hood.

### Artifact Types

| DSL Object | Schema Title | Special Properties |
|---|---|---|
| `dsl.Artifact` | system.Artifact | `.uri`, `.path`, `.name`, `.metadata` (wildcard type) |
| `dsl.Dataset` | system.Dataset | |
| `dsl.Model` | system.Model | `.framework` property |
| `dsl.Metrics` | system.Metrics | `.log_metric(name, value)` |
| `dsl.ClassificationMetrics` | system.ClassificationMetrics | `.log_roc_curve()`, `.log_confusion_matrix()` |
| `dsl.SlicedClassificationMetrics` | system.SlicedClassificationMetrics | Per-slice classification metrics |
| `dsl.HTML` | system.HTML | |
| `dsl.Markdown` | system.Markdown | |

### Artifact I/O Syntax (use this for KFP open source / RHOAI)

```python
from kfp.dsl import Input, Output, Dataset, Model, Metrics

@dsl.component
def train(dataset: Input[Dataset], model: Output[Model], metrics: Output[Metrics]):
    with open(dataset.path) as f:
        data = f.read()
    # ... train ...
    trained_model.save(model.path)
    model.metadata['framework'] = 'pytorch'
    metrics.log_metric('accuracy', 0.95)
```

Key: writing to `.path` triggers automatic upload to `.uri` by the backend.

### List of Artifacts

```python
from typing import List

@dsl.component
def merge(datasets: Input[List[Dataset]], merged: Output[Dataset]):
    all_data = []
    for ds in datasets:
        with open(ds.path) as f:
            all_data.append(f.read())
    with open(merged.path, 'w') as f:
        f.write('\n'.join(all_data))
```

## Input vs InputPath

Two ways to receive artifacts -- prefer `Input[T]` for new code:

| | `Input[T]` | `InputPath(type)` |
|---|---|---|
| Gives you | Artifact object | Raw file path string |
| Access path | `artifact.path` | `path` (is the string) |
| Access URI | `artifact.uri` | Not available |
| Access metadata | `artifact.metadata` | Not available |
| Preferred for | New KFP v2 code | Legacy / container components |

```python
# Preferred -- Input[T] (full artifact object)
@dsl.component
def train(dataset: Input[Dataset], model: Output[Model]):
    df = pd.read_csv(dataset.path)
    print(dataset.uri)
    print(dataset.metadata)

# Legacy -- InputPath (just a string path)
@dsl.component
def train_legacy(dataset_path: InputPath('Dataset')):
    df = pd.read_csv(dataset_path)  # dataset_path is a plain string
```

`OutputPath(type)` is primarily used in container components where the system provides a path to write to.

## Custom Artifact Types

Subclass `dsl.Artifact` to create domain-specific artifact types:

```python
class FeatureStore(dsl.Artifact):
    schema_title = 'custom.FeatureStore'
    schema_version = '0.0.1'

    def get_feature_count(self) -> int:
        return self.metadata.get('feature_count', 0)

@dsl.component
def produce_features(fs: Output[FeatureStore]):
    fs.metadata['feature_count'] = 42
    with open(fs.path, 'w') as f:
        f.write('features data...')

@dsl.component
def consume_features(fs: Input[FeatureStore]):
    print(f'Features: {fs.get_feature_count()}')
```

Requirements:
- Set a unique `schema_title` (format: `namespace.TypeName`)
- Optionally set `schema_version` (default `'0.0.1'`)
- `Artifact` (the base class) is a wildcard type -- it accepts any artifact subtype

## Runtime Helpers

### `dsl.get_uri()`

Returns a unique object storage URI for the current task at runtime. Only works inside a running component.

```python
@dsl.component
def custom_output(data: str):
    base_uri = dsl.get_uri()
    custom_uri = dsl.get_uri(suffix='checkpoints')
    # Write files to this unique, task-scoped location
```
