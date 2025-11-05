import json

def criar_format_json_schema(extraction_schema: dict) -> dict:
    """
    Recebe um extraction_schema simples e devolve o dicionário completo no formato:
    {
      "verbosity": "low"
      "format": {
        "type": "json_schema",
        "name": "extraction_schema",
        "strict": True,
        "schema": { ... }
      }
    }
    """

    properties = {}
    extraction_schema= extraction_schema["extraction_schema"]
    required = list(extraction_schema.keys())

    for campo, descricao in extraction_schema.items():
        prop = {
            "type": "string",
            "description": descricao
        }

        properties[campo] = prop

    schema = {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False
    }

    format_dict = {
        "format": {
            "type": "json_schema",
            "name": "extraction_schema",
            "strict": True,
            "schema": schema
        }
    }

    return format_dict