import fitz  # PyMuPDF
from typing import List, Tuple
import unicodedata
import re
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    block: int
    line: int
    wnum: int

def extract_words_with_coords(pdf_path: str, page_index: int = 0) -> List[Word]:
    """
    Retorna a lista de palavras da página com suas coordenadas.
    Coordenadas em pontos PDF (origin=top-left), medidos em pixels a ~72 dpi equivalentes.
    """
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    words_raw = page.get_text("words")  
    # words_raw: [x0, y0, x1, y1, "word", block_no, line_no, word_no]
    words = [Word(*w[:4], w[4], w[5], w[6], w[7]) for w in words_raw]
    doc.close()
    return words

def agrupar_por_linha(pdf_path: str, page_index: int = 0, y_tolerance: float = 2.0) -> List[List[Tuple[str, float, float, float, float]]]:
    """
    Lê as palavras de uma página PDF e agrupa as que pertencem à mesma linha (mesmo y) com tolerância.
    
    Retorna uma lista de linhas; cada linha é uma lista de tuplas (texto, x0, y0, x1, y1).
    """
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    words = page.get_text("words")  # [x0, y0, x1, y1, "word", block, line, word_no]
    doc.close()

    if not words:
        return []

    # ordenar por y (topo) e depois x (esquerda)
    words.sort(key=lambda w: (w[1], w[0]))

    linhas: List[List[Tuple[str, float, float, float, float]]] = []
    linha_atual: List[Tuple[str, float, float, float, float]] = []

    y_ref = words[0][1]  # y0 da primeira palavra
    for (x0, y0, x1, y1, text, *_rest) in words:
        # se estiver dentro da tolerância de y_ref, pertence à mesma linha
        if abs(y0 - y_ref) <= y_tolerance:
            linha_atual.append((text, x0, y0, x1, y1))
        else:
            # salva linha anterior (ordenada da esquerda pra direita)
            linha_atual.sort(key=lambda w: w[1])
            linhas.append(linha_atual)
            # inicia nova linha
            linha_atual = [(text, x0, y0, x1, y1)]
            y_ref = y0

    # adiciona última linha
    if linha_atual:
        linha_atual.sort(key=lambda w: w[1])
        linhas.append(linha_atual)

    return linhas



def normalizar_palavra(palavra: str) -> str:
    # 1️⃣ converte pra minúsculas
    palavra = palavra.lower()

    # 2️⃣ remove acentos (normaliza em NFD e filtra os "diacríticos")
    palavra = unicodedata.normalize("NFD", palavra)
    palavra = "".join(
        ch for ch in palavra
        if unicodedata.category(ch) != "Mn"  # Mn = Mark, Nonspacing (acentos)
    )

    # 3️⃣ remove pontuação e outros símbolos
    palavra = re.sub(r"[^a-z0-9\s]", "", palavra)

    # 4️⃣ remove espaços duplicados
    palavra = re.sub(r"\s+", " ", palavra).strip()

    return palavra


def indicar_ancoras(pdf_path: str, schema_phrase: dict) -> List[Tuple[str, float]]:
    texto_com_cordenadas = extract_words_with_coords(pdf_path)
    ancoras = []
    for word in texto_com_cordenadas:
        txt = word.text
        txt = normalizar_palavra(txt)
        if txt in schema_phrase.keys():
            ancoras.append(word)
    return ancoras

def verificar_pdfs_parecidos(pdf_path1: str, pdf_path2: str) -> bool:
    pdf_path1 = f'files/{pdf_path1}'
    pdf_path2 = f'files/{pdf_path2}'
    """
    Verifica se dois PDFs são "parecidos" com base na presença de palavras iguais em
    locais próximos.
    """
    palavras1 = extract_words_with_coords(pdf_path1)
    palavras2 = extract_words_with_coords(pdf_path2)
    count_similares = 0
    for palavra1 in palavras1:
        for palavra2 in palavras2:
            if palavra1.text == palavra2.text:
                if (abs(palavra1.x0 - palavra2.x0) < 20) and (abs(palavra1.y0 - palavra2.y0) < 20):
                    count_similares += 1
                    if count_similares >= 3:
                        return True
            if abs(palavra1.y0 - palavra2.y0) > 50:
                pass
        
    return count_similares >= 3

    

