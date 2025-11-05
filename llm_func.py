from openai import OpenAI
import os
import dotenv
from schema_func import criar_format_json_schema

def extrair_dados_com_openai(extraction_schema: dict, texto: str):
    dotenv.load_dotenv()
    API_KEY = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=API_KEY)
    response = client.responses.create(
        model="gpt-5-mini",
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Você é um agente que extrai os dados enviados pelo texto "
                            "do usuário e completa o json format com as informações encontradas\n\n"
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": texto
                    }
                ],
            },
        ],
        text=criar_format_json_schema(extraction_schema),
        reasoning={},
        tools=[],
        temperature=1,
        max_output_tokens=2048,
        top_p=1,
    )
    return response
