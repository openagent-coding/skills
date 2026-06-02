# Kubernetes Features Reference (`kfp.kubernetes`)

Separate package: `pip install kfp[kubernetes]`

Import: `from kfp import kubernetes`

All functions take a `PipelineTask` as first argument and return the modified task (chainable).

## Table of Contents
- [Secrets](#secrets)
- [ConfigMaps](#configmaps)
- [PVCs](#pvcs)
- [Ephemeral Volumes](#ephemeral-volumes)
- [EmptyDir Volumes](#emptydir-volumes)
- [Node Selectors](#node-selectors)
- [Node Affinity](#node-affinity)
- [Tolerations](#tolerations)
- [Pod Labels and Annotations](#pod-labels-and-annotations)
- [Image Pull Configuration](#image-pull-configuration)
- [Field Paths as Environment Variables](#field-paths-as-environment-variables)
- [Security Context](#security-context)
- [Timeout](#timeout)

## Secrets

### As Environment Variables

```python
kubernetes.use_secret_as_env(
    task,
    secret_name='my-secret',
    secret_key_to_env={
        'username': 'DB_USER',       # secret key -> env var name
        'password': 'DB_PASSWORD',
    },
    optional=False,  # True if secret may not exist
)
```

### As Volume Mount

```python
kubernetes.use_secret_as_volume(
    task,
    secret_name='tls-certs',
    mount_path='/etc/tls',
    optional=False,
)
```

### Multiple Secrets on Same Task

```python
kubernetes.use_secret_as_env(task, secret_name='db-creds',
    secret_key_to_env={'password': 'DB_PASSWORD'})
kubernetes.use_secret_as_env(task, secret_name='api-keys',
    secret_key_to_env={'key': 'API_KEY'}, optional=True)
```

### Apply Same Secret to Multiple Tasks

```python
for t in [download_task, train_task, eval_task]:
    kubernetes.use_secret_as_env(
        t, secret_name='hf-token',
        secret_key_to_env={'HF_TOKEN': 'HF_TOKEN'},
        optional=True,
    )
```

## ConfigMaps

### As Environment Variables

```python
kubernetes.use_config_map_as_env(
    task,
    config_map_name='app-config',
    config_map_key_to_env={
        'log_level': 'LOG_LEVEL',
        'api_url': 'API_URL',
    },
    optional=False,
)
```

### As Volume Mount

```python
kubernetes.use_config_map_as_volume(
    task,
    config_map_name='app-config',
    mount_path='/etc/config',
    optional=False,
)
```

## PVCs

### Create, Mount, and Delete

```python
pvc = kubernetes.CreatePVC(
    pvc_name_suffix='-training-data',
    access_modes=['ReadWriteOnce'],
    size='50Gi',
    storage_class_name='gp3',
    annotations={'purpose': 'training'},
)

train_task = train_model()
kubernetes.mount_pvc(train_task, pvc_name=pvc.outputs['name'], mount_path='/data')

delete = kubernetes.DeletePVC(pvc_name=pvc.outputs['name']).after(train_task)
```

### Mount Existing PVC

```python
@dsl.pipeline
def my_pipeline(pvc_name: str = 'shared-data'):
    task = process_data()
    kubernetes.mount_pvc(task, pvc_name=pvc_name, mount_path='/data')
```

### Shared PVC Between Tasks

```python
pvc = kubernetes.CreatePVC(
    pvc_name_suffix='-shared',
    access_modes=['ReadWriteMany'],
    size='10Gi',
    storage_class_name='nfs-csi',
)

producer = write_data()
consumer = read_data().after(producer)

kubernetes.mount_pvc(producer, pvc_name=pvc.outputs['name'], mount_path='/data')
kubernetes.mount_pvc(consumer, pvc_name=pvc.outputs['name'], mount_path='/data')

kubernetes.DeletePVC(pvc_name=pvc.outputs['name']).after(consumer)
```

### PVC with Data Source (volume snapshot)

```python
pvc = kubernetes.CreatePVC(
    pvc_name='restored-data',
    access_modes=['ReadWriteOnce'],
    size='100Gi',
    data_source={
        'apiGroup': 'snapshot.storage.k8s.io',
        'kind': 'VolumeSnapshot',
        'name': 'my-snapshot',
    },
)
```

## Ephemeral Volumes

```python
kubernetes.add_ephemeral_volume(
    task,
    volume_name='scratch',
    mount_path='/scratch',
    access_modes=['ReadWriteOnce'],
    size='20Gi',
    storage_class_name='gp3',
    labels={'app': 'training'},
    annotations={'purpose': 'scratch-space'},
)
```

## EmptyDir Volumes

```python
kubernetes.empty_dir_mount(
    task,
    volume_name='cache',
    mount_path='/tmp/cache',
    medium=None,        # or 'Memory' for tmpfs
    size_limit='5Gi',
)
```

## Node Selectors

```python
kubernetes.add_node_selector(task, label_key='disktype', label_value='ssd')
kubernetes.add_node_selector(task, label_key='nvidia.com/gpu.present', label_value='true')
```

### JSON Variant (supports pipeline parameters)

```python
kubernetes.add_node_selector_json(task, node_selector_json={
    'disktype': 'ssd',
    'zone': 'us-east-1a',
})
```

## Node Affinity

### Required Affinity

```python
kubernetes.add_node_affinity(
    task,
    match_expressions=[
        {'key': 'kubernetes.io/os', 'operator': 'In', 'values': ['linux']},
        {'key': 'gpu-type', 'operator': 'In', 'values': ['a100', 'v100']},
    ],
    # weight=None means required
)
```

### Preferred Affinity

```python
kubernetes.add_node_affinity(
    task,
    match_expressions=[
        {'key': 'zone', 'operator': 'In', 'values': ['us-east-1a']},
    ],
    weight=80,  # 1-100, higher = stronger preference
)
```

Valid operators: `In`, `NotIn`, `Exists`, `DoesNotExist`, `Gt`, `Lt`

### JSON Variant

```python
kubernetes.add_node_affinity_json(task, node_affinity_json={...})
```

## Tolerations

```python
kubernetes.add_toleration(
    task,
    key='nvidia.com/gpu',
    operator='Equal',       # 'Equal' or 'Exists'
    value='present',
    effect='NoSchedule',    # 'NoSchedule', 'PreferNoSchedule', 'NoExecute'
    toleration_seconds=3600,
)
```

### Tolerate All Taints

```python
kubernetes.add_toleration(task, operator='Exists')
```

### JSON Variant

```python
kubernetes.add_toleration_json(task, toleration_json=[
    {'key': 'dedicated', 'operator': 'Equal', 'value': 'ml', 'effect': 'NoSchedule'},
])
```

## Pod Labels and Annotations

```python
kubernetes.add_pod_label(task, label_key='app', label_value='training')
kubernetes.add_pod_label(task, label_key='team', label_value='ml-platform')

kubernetes.add_pod_annotation(task, annotation_key='run_id', annotation_value='abc123')
```

## Image Pull Configuration

```python
kubernetes.set_image_pull_policy(task, 'IfNotPresent')  # 'Always', 'Never', 'IfNotPresent'
kubernetes.set_image_pull_secrets(task, secret_names=['registry-creds', 'quay-creds'])
```

## Field Paths as Environment Variables

Inject pod metadata into environment variables:

```python
kubernetes.use_field_path_as_env(task, env_name='POD_NAME', field_path='metadata.name')
kubernetes.use_field_path_as_env(task, env_name='POD_NAMESPACE', field_path='metadata.namespace')
kubernetes.use_field_path_as_env(task, env_name='NODE_NAME', field_path='spec.nodeName')
kubernetes.use_field_path_as_env(task, env_name='POD_IP', field_path='status.podIP')
```

## Security Context

```python
kubernetes.set_security_context(
    task,
    run_as_user=1000,
    run_as_group=1000,
    run_as_non_root=True,
)
```

Platform defaults (enforced by compiler, cannot be overridden):
- `allowPrivilegeEscalation=false`
- Drop ALL capabilities
- `seccompProfile=RuntimeDefault`

## Timeout

```python
kubernetes.set_timeout(task, seconds=3600)  # maps to pod activeDeadlineSeconds
```
