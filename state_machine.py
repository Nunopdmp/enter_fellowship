from pdf_func import agrupar_por_linha, verificar_pdfs_parecidos, extract_words_with_coords
from schema_func import criar_format_json_schema
from openai import OpenAI
import dotenv
import os
import json
import time

def state_machine(dataset_path: str,
                  nome_da_pasta_dos_pdfs: str,
                  on_step=None):
    """
    on_step: função chamada a cada PDF processado.
             Assinatura sugerida: on_step(idx, total, response_dict)
    """
    solucao = []
    dotenv.load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    memoria_cache = []

    with open(dataset_path, 'r', encoding='utf-8') as f:
        lista_label = json.load(f)

    total = len(lista_label)

    for idx, label in enumerate(lista_label, start=1):
        pdf_path = label["pdf_path"]
        pdf_path = f"{nome_da_pasta_dos_pdfs}/{pdf_path}"

        if hard_response_enabled(memoria_cache, label):
            new_label, parcial_response = hard_response(memoria_cache, label)
            if new_label:
                texto = agrupar_por_linha(pdf_path, y_tolerance=4)
                # aqui tua llm_resonse já devolve string, então converto
                resp_str = llm_resonse(client, new_label, texto)
                resp_dict = concat(parcial_response, json.loads(resp_str))
            else:
                resp_dict = parcial_response
        else:
            texto = agrupar_por_linha(pdf_path, y_tolerance=4)
            resp_str = llm_resonse(client, label, texto)
            resp_dict = json.loads(resp_str)

        memoria_cache = chache_memory(memoria_cache, label, resp_dict)
        solucao.append(resp_dict)

        # 🔴 aqui é o ponto: chama o callback pra quem quiser mostrar em tempo real
        if on_step is not None:
            pdf_name = os.path.basename(pdf_path)
            on_step(idx, total, pdf_name, resp_dict)

    return solucao

def hard_response_enabled(memoria_cache, label_case: dict) -> bool:
    count = 0
    for old_label in memoria_cache:
        if old_label["label"] == label_case["label"]:
            count += 1

    return count > 10

def concat(partial_response: dict, llm_response: dict) -> dict:

    for key in partial_response.keys():
        llm_response[key] = partial_response[key]

    return llm_response


def hard_response(memoria_cache: list, label_case: dict):
    tips = []
    for old_label in memoria_cache:
        if old_label["label"] == label_case["label"]:
            old_label_response = old_label["response"]
            pdf_file_path_old_label = old_label["pdf_path"]
            tips.append((old_label_response, pdf_file_path_old_label))
    """are pdfs equal?"""
    for old_label_response, pdf_file_path_old_label in tips:
        if verificar_pdfs_parecidos(pdf_file_path_old_label, label_case["pdf_path"]): # precisa ser ajustado
            for key_response in old_label_response.keys():
                if key_response not in label_case["extraction_schema"].keys():
                    tips.remove((old_label_response, pdf_file_path_old_label))
        else:
            tips.remove((old_label_response, pdf_file_path_old_label))
    """tips ready to use, they have somebody extraction_schema similar 
        and are similar pdfs"""
    """tips are list of tuples (old_label_response, pdf_file_path_old_label) that can be used to extract coordinates"""
    if tips:
        candidatos = []
        for old_label_response, pdf_file_path_old_label in tips:
            for key in old_label_response.keys():
                if key in label_case["extraction_schema"].keys() and old_label_response[key]: #é uma chave possível de se extrair coredenadas
                    candidatos.append({"key": key, "old_response": old_label_response[key], "pdf_path": pdf_file_path_old_label})
        cordenates = []
        for element in candidatos:
            texto = extract_words_with_coords(f'files/{element["pdf_path"]}')
            for word in texto:
                if word.text == element["old_response"]:
                    cordenates.append({"key": element["key"], "coords": (word.x0, word.y0, word.x1, word.y1), "pdf_path": element["pdf_path"]})
        lista_de_contagem = {}
        for elemento in cordenates:
            key = elemento["key"]
            if key in lista_de_contagem.keys():
                lista_de_contagem[key] +=1
            else:
                lista_de_contagem[key] =1
        lista_de_keys_que_ja_foram_usadas = []
        parcial_response = {}
        new_label = label_case
        for elemento in cordenates:
            centers = []
            key = elemento["key"]
            if key in lista_de_keys_que_ja_foram_usadas:
                continue
            else:
                
                if lista_de_contagem[key] >= 2:
                    x0, y0, x1, y1 = elemento["coords"]
                    center_x = (x0 + x1) / 2
                    center_y = (y0 + y1) / 2
                    if centers == []:
                        centers.append((center_x, center_y, 1))
                    else:
                        for element in centers:
                            x_c, y_c, count = element
                            if abs(center_x - x_c) < 5 and abs(center_y - y_c) < 5: #decisions
                                count += 1
                            else:
                                centers.append((center_x, center_y, 1))
                max_count = 0
                sum_count = 0
                element_whith_max_count = None
                for element in centers:
                    x_c, y_c, count = element
                    sum_count += count
                    if count > max_count:
                        max_count = count
                        element_whith_max_count = element
                if max_count / sum_count > 0.6: 
                    texto = extract_words_with_coords(f'files/{elemento["pdf_path"]}')
                    x_c, y_c, count = element_whith_max_count
                    for word in texto:
                        x0, y0, x1, y1 = word.x0, word.y0, word.x1, word.y1
                        center_x = (x0 + x1) / 2
                        center_y = (y0 + y1) / 2
                        if abs(center_x - x_c) < 5 and abs(center_y - y_c) < 5: #decisions
                            response = word.text
                            parcial_response[elemento["key"]] = response
                            lista_de_keys_que_ja_foram_usadas.append(elemento["key"])
                            del new_label["extraction_schema"][elemento["key"]]
        return new_label, parcial_response
    else:
        return label_case, {}

    

def llm_resonse(client: OpenAI, label_case: dict, texto: str):
    texto_str = ""
    for w in texto:
        linha_texto = " ".join([t[0] for t in w])
        texto_str += f"Linha {texto.index(w)+1}: {linha_texto}\n"
    estimativa_tokens_input = len(texto_str + str(criar_format_json_schema(label_case)))/4
    
    response = client.responses.create(
            model="gpt-5-mini",
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Você é um agente de EXTRAÇÃO ESTRITA de campos de um documento.\n"
                                f"O documento que você está analisando é do tipo: {label_case['label']}.\n"
                                "REGRAS IMPORTANTES:\n"
                                "1. Use exatamente o texto do documento quando o campo existir (não traduza, não escreva por extenso, não mude 'PR' para 'Paraná').\n"
                                "2. Se o valor aparecer em maiúsculas no documento, mantenha maiúsculas.\n"
                                "3. Se o endereço vier quebrado em várias linhas, junte na mesma ordem em que aparecem.\n"
                                "4. Se o campo não existir, deixe-o vazio.\n"
                                "5. Retorne SOMENTE o JSON final, sem comentários.\n"
                                "6. O documento está numerado por linhas. Use essas linhas para localizar os campos.\n"
                                "7. NÃO invente DDD nem número de telefone se não existir.\n"
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text",
                                  "text": (texto_str + "dados para extração:" + str(label_case["extraction_schema"].keys()))}],
                },
            ],
            text=criar_format_json_schema(label_case),
            reasoning={"effort": "low"},
            max_output_tokens=int(3*estimativa_tokens_input),
            top_p=1,
        )

    return response.output[1].content[0].text

def chache_memory(memoria_cache: list, label_case: dict, response_text: str):
    try:
        response_dic = response_text
        if memoria_cache:
            lista_de_labels = []
            for old_label in memoria_cache:
                lista_de_labels.append(old_label["label"])
            if label_case["label"] in lista_de_labels:
                count = lista_de_labels.count(label_case["label"])
                if count < 30:
                    memoria_cache.append({
                        "pdf_path": label_case["pdf_path"],
                        "label": label_case["label"],
                        "schema": label_case["extraction_schema"],
                        "response": response_dic
                        })
                else:
                    pass
            else:
                memoria_cache.append({
                        "pdf_path": label_case["pdf_path"],
                        "label": label_case["label"],
                        "schema": label_case["extraction_schema"],
                        "response": response_dic
                        })
        else:
            memoria_cache.append({
                        "pdf_path": label_case["pdf_path"],
                        "label": label_case["label"],
                        "schema": label_case["extraction_schema"],
                        "response": response_dic
                        })
    except Exception as e:
        print("Erro ao salvar na memória cache:", e)

    return memoria_cache





