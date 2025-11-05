# app.py
import streamlit as st
import os
import json
import tempfile
from io import BytesIO
from PIL import Image  # se quiser mostrar a logo

from openai import OpenAI

# importa tuas funções do teu arquivo
# (ajuste o nome/path conforme estiver no teu projeto)
from state_machine import (
    llm_resonse,
    state_machine,
    agrupar_por_linha,   # se estiver em outro arquivo, importa de lá
)

import dotenv
dotenv.load_dotenv()

st.set_page_config(page_title="ENTER - Extração de PDFs", layout="wide")

# === ESTILO RÁPIDO (opcional, além do config.toml) ===
st.markdown("""
<style>
/* ======== FUNDO GERAL ======== */
.main, .block-container {
    background-color: #000000 !important;
}

/* ======== TEXTOS (brancos) ======== */
h1, h2, h3, h4, h5, h6, p, label, span, div, textarea, .stMarkdown, .stText, .stSelectbox label {
    color: #FFFFFF !important;
}

/* ======== BOTÕES (laranjas) ======== */
.stButton>button {
    background-color: #F6A623 !important;
    color: #000000 !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    transition: 0.3s ease all !important;
}

.stButton>button:hover {
    background-color: #d88d00 !important;
    color: #000000 !important;
}

/* ======== CAMPOS DE ENTRADA ======== */
.stTextArea textarea,
.stTextInput input,
.stFileUploader,
.stSelectbox div[data-baseweb="select"] {
    background-color: #1A1A1A !important;
    color: #FFFFFF !important;
    border: 1px solid #333333 !important;
    border-radius: 6px !important;
}

/* ======== TÍTULO CENTRALIZADO (opcional) ======== */
h1 {
    color: #FFFFFF !important;
    text-align: left;
    font-weight: 800;
}
</style>
""", unsafe_allow_html=True)


# mostra logo no topo (ajusta o caminho da imagem)
# se o arquivo estiver na mesma pasta do app:
try:
    logo = Image.open("enter_logo.png")  # renomeia o arquivo que você tem
    st.image(logo, width=160)
except Exception:
    st.write("")  # se não achar a imagem, segue o jogo

st.title("ENTER – Extração de dados")
modo = st.sidebar.selectbox("Modo de requisição", ["Único", "Batch"])


# -----------------------------------------------------------
# MODO ÚNICO
# -----------------------------------------------------------
if modo == "Único":
    st.subheader("Modo único")

    uploaded_pdf = st.file_uploader("Envie o PDF", type=["pdf"])
    label_json_str = st.text_area(
        "Cole o JSON do label + extraction_schema",
        value='{\n  "label": "carteira_oab",\n  "extraction_schema": {\n    "nome": "Nome do profissional, normalmente no canto superior esquerdo da imagem"\n  }\n}',
        height=200
    )
    run_button = st.button("Extrair")

    if run_button:
        if uploaded_pdf is None:
            st.error("Envie um PDF primeiro.")
        else:
            # salva PDF temporariamente pra poder passar o path
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                tmp_pdf.write(uploaded_pdf.read())
                tmp_pdf_path = tmp_pdf.name

            try:
                label_case = json.loads(label_json_str)
            except json.JSONDecodeError:
                st.error("O JSON do label está inválido.")
                st.stop()

            # cria client
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # pega o texto do pdf (usando tua função)
            texto = agrupar_por_linha(tmp_pdf_path, y_tolerance=4)

            # chama tua função de LLM
            resp_str = llm_resonse(client, label_case, texto)

            # tenta converter pra dict só pra mostrar bonito
            try:
                resp_dict = json.loads(resp_str)
            except Exception:
                resp_dict = {"raw_response": resp_str}

            st.success("Extração concluída!")
            st.json(resp_dict)


# ==============================
# MODO BATCH
# ==============================
else:
    st.subheader("Modo batch")

    # 🔝 lugar onde o botão de download vai aparecer DEPOIS
    download_ph = st.empty()

    dataset_file = st.file_uploader("Envie o dataset JSON", type=["json"])
    pdfs_files = st.file_uploader("Envie os PDFs (vários)", type=["pdf"], accept_multiple_files=True)

    run_batch = st.button("Rodar batch")

    if run_batch:
        if dataset_file is None:
            st.error("Envie o dataset JSON.")
            st.stop()
        if not pdfs_files:
            st.error("Envie ao menos um PDF.")
            st.stop()

        tmp_dir = tempfile.mkdtemp()
        pdfs_dir = os.path.join(tmp_dir, "pdfs")
        os.makedirs(pdfs_dir, exist_ok=True)

        dataset_path = os.path.join(tmp_dir, "dataset.json")
        with open(dataset_path, "wb") as f:
            f.write(dataset_file.read())

        for up in pdfs_files:
            with open(os.path.join(pdfs_dir, up.name), "wb") as f:
                f.write(up.read())

        st.info("Iniciando processamento...")

        progress_ph = st.empty()
        log_ph = st.empty()
        lista_container = st.container()

        resultados_finais = []
        per_item_placeholders = {}

        def streamlit_callback(idx, total, pdf_name, resp_dict):
            progress_ph.progress(idx / total, text=f"Processando {idx}/{total}")
            resultados_finais.append(resp_dict)

            if idx not in per_item_placeholders:
                per_item_placeholders[idx] = lista_container.container()

            with per_item_placeholders[idx]:
                st.markdown(f"**Resultado do PDF {idx}/{total}: `{pdf_name}`**")
                st.json(resp_dict)

            with log_ph:
                st.write(f"✅ {pdf_name} ({idx}/{total}) processado.")

        final_results = state_machine(
            dataset_path=dataset_path,
            nome_da_pasta_dos_pdfs=pdfs_dir,
            on_step=streamlit_callback
        )

        st.success("Batch finalizado!")

        # 🔝 agora que terminou, colocamos o botão LÁ EM CIMA
        download_ph.download_button(
            label="⬇️ Baixar resultados (JSON)",
            data=json.dumps(final_results, ensure_ascii=False, indent=2),
            file_name="resultados_batch.json",
            mime="application/json"
        )