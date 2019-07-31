# Migrating an APB to an Ansible Operator

## Basic process
### Directory structure and metadata
1. Generate an operator with operator-sdk new <name> --type=ansible --api-version=<group>/<version> --kind=<kind>
1. Take the build, deploy, and molecule directories, as well as the watches.yaml and copy them into your APB directory
1. You now have two Dockerfiles, your original `apb` Dockerfile at the top-level, and a `build/Dockerfile` for your operator. Ensure that your playbooks and roles are copied to `${HOME}/roles` and `${HOME}/playbooks`, and that your `watches.yaml` is being copied to `${HOME}/watches.yaml`. If you are installing any additional dependencies, ensure that those are reflected in your `build/Dockerfile` as well. You may remove your original `apb` Dockerfile.
1. In the `watches.yaml`, ensure the playbook for your `kind` points to your `provision.yml` playbook in the container (likely location for that will be `/opt/ansible/playbooks/provision.yml`). 
1. In the `watches.yaml`, add a finalizer block with a name of: `<name>.<group>/<version>`, and set the playbook to point to your `deprovision.yml` in the container (likely location for that will be `/opt/ansible/playbooks/deprovision.yml`).
1. If you have a `bind` playbook, add a new entry to your `watches.yaml` (you can copy paste the first one). The `version` and `group`, will remain unchanged, but update the `kind` with a `Binding` suffix. For example, if you have a resource with `kind: Keycloak`, the kind of your new resource will be `KeycloakBinding`. The playbook for this entry should map to your `bind` playbook, (likely location `/opt/ansible/playbooks/bind.yml`), and if you have an `unbind` playbook then set the playbook for your finalizer to point to it (likely location `/opt/ansible/playbooks/unbind.yml`). You will also need to run `operator-sdk add crd --api-version=<group>/<version> --kind=<kind>` to generate a new CRD and example in `deploy/crds`.
1. Now that you have all your CRDs created, you can generate the OpenAPI spec for them using your apb.yml. The `convert.py` script can handle the conversion to the OpenAPI spec, at which point you can copy paste everything from `validation:` on into your primary CRD (for the regular `parameters`), or into your `Binding` CRD (for `bind_parameters`).
1. You may notice that the OpenAPI validation uses `camelCase` parameters, while your `apb.yml` and Ansible playbooks probably assume `snake_case` variables. `Ansible Operator` will automatically convert the `camelCase` parameters from the Kubernetes resource into `snake_case` before passing them to your playbook, so this should not require any change on your part.

### Ansible logic
There will be some changes required to your Ansible playbooks/roles/tasks.

#### asb_encode_binding
This module will not be present in the Ansible Operator base image. In order to save credentials after a successful provision, you will need to create a `secret` in Kubernetes, and update the status of your custom resource so that people can find it. For example, if we have the following Custom Resource:

```yaml
version: v1alpha1
group: apps.example.com
kind: PostgreSQL
```

the following task:

```yaml
- name: encode bind credentials
  asb_encode_binding:
    fields:
      DB_TYPE: postgres
      DB_HOST: "{{ app_name }}"
      DB_PORT: "5432"
      DB_USER: "{{ postgresql_user }}"
      DB_PASSWORD: "{{ postgresql_password }}"
      DB_NAME: "{{ postgresql_database }}"
```

would become:

```yaml
- name: Create bind credential secret
  k8s:
    definition:
      apiVersion: v1
      kind: Secret
      metadata:
        name: '{{ meta.name }}-credentials'
        namespace: '{{ meta.namespace }}'
      data:
        DB_TYPE: "{{ 'postgres' | b64encode }}"
        DB_HOST: "{{ app_name | b64encode }}"
        DB_PORT: "{{ '5432' | b64encode }}"
        DB_USER: "{{ postgresql_user | b64encode }}"
        DB_PASSWORD: "{{ postgresql_password | b64encode }}"
        DB_NAME: "{{ postgresql_database | b64encode }}"

- name: Attach secret to CR status
  k8s_status:
    api_version: apps.example.com/v1alpha1
    kind: PostgreSQL
    name: '{{ meta.name }}'
    namespace: '{{ meta.namespace }}'
    status:
      bind_credentials_secret: '{{ meta.name }}-credentials'
```


# scratch
* Playbooks and roles shouldn't need to change much
* provision.yml -> the playbook specified in watches.yaml
* deprovision.yml -> the finalizer playbook specified in watches.yaml

## ansible_kubernetes_modules
* The ansible_kubernetes_modules role and the generated modules are now deprecated.
* The `k8s` module was added in Ansible 2.6 and is the supported way to interact with Kubernetes from Ansible.
* The `k8s` module takes normal kubernetes manifests, so if you currently rely on the old generated modules some refactoring will be required.

## apb.yml
* Pieces of the apb.yml will move to the Custom Resource Definition
* No concept of plans with operators, will need to merge configuration into single CRD

## Bindings
* Operators have no concept of a binding
* Can be represented as a secondary Custom Resource
* Store the (or point to secret containing) results in the status of the <APP>Binding resource

### asb_encode_binding
* Rather than writing out your credentials here, you will instead create a secret that contains them, and then use the `k8s_status` module to add a reference to that secret to the status of your CR.

## Example watches.yaml

```
---
- version: v1alpha1
  group: apps.keycloak.org
  kind: Keycloak
  playbook: /opt/ansible/playbooks/provision.yml
  finalizer:
    name: finalizer.apps.keycloak.org/v1alpha1
    playbook: /opt/ansible/playbooks/deprovision.yml

- version: v1alpha1
  group: apps.keycloak.org
  kind: KeycloakBinding
  playbook: /opt/ansible/playbooks/bind.yml
  finalizer:
    name: finalizer.apps.keycloak.org/v1alpha1
    playbook: /opt/ansible/playbooks/unbind.yml
```

## Terms
kind
group
apiVersion
watches.yaml
finalizer
CRD


