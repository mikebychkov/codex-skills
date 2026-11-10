"""Fail-closed interpreter for the JSON Schema keywords used by our bundled contract.

Not a general JSON Schema implementation. Supports local refs, object/array/string/
integer types, properties, required, additionalProperties, items, min/maxItems,
uniqueItems, pattern, minimum, enum, const, allOf, oneOf. Standard validators can
also consume the bundled Draft 2020-12 schema. Unsupported keywords fail closed.
"""
import re

SUPPORTED = {'$schema', '$defs', '$ref', 'title', 'description', 'type', 'properties',
             'required', 'additionalProperties', 'items', 'minItems', 'maxItems',
             'uniqueItems', 'pattern', 'minimum', 'enum', 'const', 'allOf', 'oneOf'}


def check_schema(schema):
    if not isinstance(schema, dict):
        raise ValueError('Schema nodes must be objects')
    unknown = set(schema) - SUPPORTED
    if unknown:
        raise ValueError(f'Unsupported schema keywords: {sorted(unknown)}')
    for key in ('properties', '$defs'):
        for child in schema.get(key, {}).values():
            check_schema(child)
    for key in ('allOf', 'oneOf'):
        for child in schema.get(key, []):
            check_schema(child)
    if 'items' in schema:
        check_schema(schema['items'])


def validate(instance, schema):
    check_schema(schema)

    def walk(value, node, path):
        errors = []
        if '$ref' in node:
            reference = node['$ref']
            if not reference.startswith('#/$defs/'):
                raise ValueError('Only local $defs refs supported')
            errors.extend(walk(value, schema['$defs'][reference.split('/')[-1]], path))
        kind = node.get('type')
        matches = {'object': isinstance(value, dict), 'array': isinstance(value, list),
                   'string': isinstance(value, str), 'integer': type(value) is int}
        if kind and not matches.get(kind, False):
            return [f'{path}: expected {kind}']
        if 'const' in node and (type(value) != type(node['const']) or value != node['const']):
            errors.append(f'{path}: expected constant {node["const"]!r}')
        if 'enum' in node and value not in node['enum']:
            errors.append(f'{path}: expected one of {node["enum"]}')
        if isinstance(value, dict):
            for name in node.get('required', []):
                if name not in value:
                    errors.append(f'{path}.{name}: required')
            properties = node.get('properties', {})
            if node.get('additionalProperties') is False:
                for name in value.keys() - properties.keys():
                    errors.append(f'{path}.{name}: unknown field')
            for name in value.keys() & properties.keys():
                errors.extend(walk(value[name], properties[name], f'{path}.{name}'))
        if isinstance(value, list):
            if len(value) < node.get('minItems', 0):
                errors.append(f'{path}: requires at least {node["minItems"]} items')
            if 'maxItems' in node and len(value) > node['maxItems']:
                errors.append(f'{path}: allows at most {node["maxItems"]} items')
            if node.get('uniqueItems') and any(item in value[:i] for i, item in enumerate(value)):
                errors.append(f'{path}: duplicate items')
            for i, item in enumerate(value):
                errors.extend(walk(item, node.get('items', {}), f'{path}[{i}]'))
        if isinstance(value, str) and 'pattern' in node and not re.search(node['pattern'], value):
            errors.append(f'{path}: does not match {node["pattern"]}')
        if type(value) is int and 'minimum' in node and value < node['minimum']:
            errors.append(f'{path}: minimum is {node["minimum"]}')
        for child in node.get('allOf', []):
            errors.extend(walk(value, child, path))
        if 'oneOf' in node:
            branches = [walk(value, child, path) for child in node['oneOf']]
            if sum(not branch for branch in branches) != 1:
                errors.append(f'{path}: status-specific requirements not met')
                # Include the closest branch's errors for actionable diagnostics.
                errors.extend(min(branches, key=len))
        return errors

    return sorted(set(walk(instance, schema, '$')))
