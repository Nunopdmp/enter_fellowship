# Solução para o desafio 

## 🧠 Como usar o projeto

### 🛠️ Pré-requisitos

Certifique-se de ter o **Python 3.13** instalado.
Depois, instale todas as dependências necessárias com:

```bash
pip install -r requirements.txt
```

---
Certifique-se de criar o arquivo 
```bash
.env
```
e adicionar a sua api_key da openai
```bash
OPENAI_API_KEY = sk-...
```
### 🚀 Executando a aplicação

A interface do projeto foi construída com **Streamlit**, permitindo o uso de forma simples e intuitiva — tanto para o processamento de **um único PDF** quanto para **vários arquivos em lote**.

Para iniciar a aplicação, execute no terminal:

```bash
streamlit run app.py
```

Isso abrirá automaticamente a interface web no navegador.
A partir dela, você poderá:

* Fazer **upload de um PDF** e de seu **label/schema em formato JSON**;
* Obter a saída estruturada com os campos extraídos;
* Alternar para o modo **batch**, selecionando uma **pasta contendo vários PDFs** e um **dataset.json** com os labels correspondentes.

---

### 🧩 Função principal: `estate_machine()`

Toda a orquestração do pipeline está concentrada na função:

```python
def state_machine(dataset_path: str,
                  nome_da_pasta_dos_pdfs: str,
                  on_step=None):
```

Ela é responsável por:

* Ler o schema JSON e o arquivo PDF;
* Executar as etapas de pré-processamento (como agrupamento de linhas e verificação de similaridade);
* Decidir, de forma adaptativa, se o resultado pode ser reutilizado do cache ou se é necessário invocar o modelo LLM;
* Retornar o JSON final com as informações estruturadas conforme o schema solicitado.

Essa função representa o **núcleo lógico do sistema** e garante o equilíbrio entre custo, velocidade e precisão.

---

## ⚙️ Otimização e Estratégia de *Hard Response*

Uma das principais preocupações deste projeto foi equilibrar **tempo de execução, custo e precisão**, especialmente considerando que múltiplas chamadas à API da OpenAI tornam o processo caro e lento.
Para mitigar esse problema, foi desenvolvida a rotina **`hard_response()`**, inspirada em mecanismos de **treinamento em batch** utilizados em *Machine Learning*.

---

### 🎯 Objetivo

A ideia central foi **aproveitar o comportamento repetitivo de PDFs com layout semelhante**.
Enquanto documentos de um mesmo *label* compartilham padrões estruturais, a IA pode cometer os mesmos acertos e erros de forma consistente.
Assim, foi criada uma heurística que **aprende com as respostas anteriores** e **replica as extrações bem-sucedidas**, reduzindo drasticamente o número de chamadas ao modelo LLM.

---

### 🧠 Funcionamento

1. **Memória Cache:**
   Cada solicitação é armazenada em uma estrutura de memória (`memoria_cache`), contendo tanto o *label* quanto as coordenadas e respostas obtidas.

2. **Verificação de Similaridade:**
   Quando um novo PDF é processado, o sistema compara seu layout e regiões de texto com documentos já vistos.
   Caso sejam **suficientemente semelhantes**, o sistema identifica **regiões de coordenadas próximas** e tenta **extrair os campos diretamente** dessas áreas, sem invocar o LLM.

3. **Hard Response:**
   Se a semelhança ultrapassa o limiar definido, a função `hard_response()` é acionada — aplicando diretamente as respostas armazenadas anteriormente.
   Essa técnica mostrou-se eficaz, sendo capaz de **substituir com sucesso cerca de 60% das chamadas ao modelo**, garantindo custo reduzido e resposta quase instantânea.

---

### ⚖️ Trade-offs e Decisões de Projeto

Essa abordagem é uma **faca de dois gumes**:

* Se o modelo estava **acertando 60% das vezes**, o *hard response* passa a acertar esses casos **100% das vezes**, consolidando o acerto.
* Porém, **erros acurados também são propagados**.

Por isso, foi feito um investimento cuidadoso em **Prompt Engineering**, buscando **instruções altamente específicas e contextuais** que aumentassem a taxa de acerto natural do modelo antes mesmo do uso de cache.

Optou-se por **não ampliar o hard_response com heurísticas estatísticas complexas**, mantendo a estratégia **conservadora e barata por iteração**, priorizando eficiência e reprodutibilidade.

---

### 🧩 Estratégias Avaliadas e Decisões

* ❌ **Bag of Words:**
  Descartada. Apesar de útil para análise textual, exigiria contextos amplos para cada chave, gerando sobreposição de tokens e custo elevado.

* ❌ **Chamada individual por chave:**
  Também descartada. Muitas chaves não possuem correlação direta no texto, o que obrigaria enviar o documento completo repetidas vezes.

* ✅ **Prompt Engineering refinado:**
  Adotado como estratégia principal.
  Dada a natureza dos PDFs (apenas uma página), foi possível alcançar excelente desempenho apenas com ajustes no prompt e controle de contexto.

---

### 💡 Conclusão

A função `hard_response()` atua como um **mecanismo de memória inteligente**, replicando o comportamento de aprendizado incremental de modelos de ML sem custo adicional de inferência.
Essa solução, combinada com **prompt engineering e cache adaptativo**, resultou em uma arquitetura **rápida, barata e robusta**, capaz de lidar com variações de layout mantendo alta precisão.

---

## 🔄 Solução Avançada: Pipeline em Malha de Controle

Durante o desenvolvimento, considerei uma solução mais sofisticada, inspirada em **sistemas de controle moderno**, que embora promissora, ultrapassava o escopo temporal do desafio (uma semana).

A ideia seria estruturar o processo de extração em uma **malha de controle fechada**, na qual o sistema **avaliaria e corrigiria iterativamente suas próprias saídas** — uma analogia direta a um **controlador PID/PNL** (Proporcional–Não Linear) ajustando o erro entre o estado atual e o desejado.

---

### 🧠 Conceito

Nessa arquitetura, os **outputs anteriores** seriam **realimentados como inputs** para um **algoritmo de avaliação PNL (Programação Neurolinguística / heurística de controle não linear)**.
Esse módulo compararia as respostas das chaves extraídas entre si, identificando **discrepâncias semânticas ou inconsistências lógicas** (por exemplo, divergências entre nome e gênero, ou se a categoria declarada contradiz o tipo de documento).

O sistema faria então um **“juízo de valor”** sobre a adequação de cada campo, ajustando as respostas dentro de uma **pipeline iterativa em malha fechada** — refinando progressivamente o resultado até convergir para a extração mais coerente e estável.

---

### ⚙️ Funcionamento Proposto

1. **Extração inicial (malha aberta):**
   O LLM executa a primeira extração com base no schema e texto bruto.

2. **Comparação e avaliação (malha de realimentação):**
   O módulo de controle avalia a consistência interna das respostas e as compara com padrões aprendidos de PDFs similares.

3. **Correção e reentrada:**
   Caso identifique inconsistências, o sistema ajusta localmente os valores (proporcional e não linearmente), retroalimentando o resultado na pipeline — sem necessidade de nova chamada à API da OpenAI.

4. **Convergência:**
   O processo se repete até o erro médio (diferença semântica entre chaves correlatas) atingir um limite aceitável.

---

### 💰 Custo e Trade-off

Implementar essa abordagem aumentaria o custo da solução — tanto em termos computacionais quanto de engenharia.
Apesar de reduzir drasticamente a dependência de chamadas externas ao LLM, exigiria:

* Calibração do módulo PNL local;
* Criação de métricas semânticas de erro específicas por tipo de campo;
* Mecanismo de retroalimentação controlada para garantir estabilidade da malha.

Por isso, optei por **não implementá-la nesta fase**, priorizando uma solução **eficiente, estável e de baixo custo**, mas a arquitetura atual foi construída de forma que **essa extensão possa ser integrada futuramente**.

---

### 🧩 Potencial Futuro

A aplicação de **conceitos de controle em pipelines de IA** abre caminho para soluções mais autônomas e autoavaliativas — verdadeiros **sistemas de extração com autoconfiança**.
No contexto deste projeto, essa integração poderia oferecer um **“fine-tuning iterativo local”** sem aumentar o número de chamadas às APIs, transformando o sistema em uma **malha adaptativa de autovalidação semântica**.

---


