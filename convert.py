#!/usr/bin/env python

import yaml


def extract_params(all_params):
    properties = {}
    required = set()
    for param in all_params:
        name = param['name']
        name_parts = name.split('_')
        camel_name = name_parts[0] + ''.join([x.title() for x in name_parts[1:]])
        if param.get('required') is True:
            if camel_name not in properties:
                required.add(camel_name)
        elif camel_name in required and param.get('required') is False:
            required.remove(camel_name)
        properties[camel_name] = {
            "type": param["type"],
            "description": param.get("description", param.get("title", ""))
        }

    openapi_spec = {
        "validation": {"openAPIv3Schema": {
            "properties": {
                "spec": {
                    "required": list(required),
                    "properties": properties
                }
            }
        }}
    }

    return openapi_spec


def main():
    with open('apb.yml', 'r') as f:
        apb_meta = yaml.safe_load(f.read())

    for field in ['parameters', 'bind_parameters']:
        print("Converting {0} to OpenAPI spec".format(field))
        print(yaml.dump({field: extract_params([
            param for x in apb_meta['plans'] for param in x.get(field, [])
        ])}))


if __name__ == '__main__':
    main()
