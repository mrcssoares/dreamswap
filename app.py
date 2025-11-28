import streamlit as st
from tavily import TavilyClient
from openai import OpenAI
import json
import os
from datetime import datetime
from gtts import gTTS
from io import BytesIO
from elevenlabs.client import ElevenLabs
import streamlit as st
import requests
from streamlit_lottie import st_lottie

# Função para carregar animações Lottie (JSON)
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# Carregando assets (Animações)
lottie_loading = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_tloqiupn.json") # Foguete
lottie_coach = load_lottieurl("https://assets3.lottiefiles.com/packages/lf20_m64r7bqm.json")   # Leão/Coach
# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="DreamSwap AI", page_icon="🚀", layout="centered")

# --- MEMÓRIA GLOBAL COMPARTILHADA ---
@st.cache_resource
def get_historico_global():
    return []

historico = get_historico_global()

# --- MÉLIUZ PARTNERS ---
@st.cache_data
def get_meliuz_partners():
    try:
        url = "https://s3.sa-east-1.amazonaws.com/static.meliuz.com.br/client-site-static/partners-list.json"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get('partners', []) # Retorna a lista de parceiros
    except:
        pass
    return []

meliuz_partners = get_meliuz_partners()

def normalize_string(s):
    # Remove espaços, acentos e deixa minúsculo
    import unicodedata
    return "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower().replace(" ", "")

def check_meliuz_cashback(url, partners):
    # Lógica de match melhorada
    domain = url.lower().replace("https://", "").replace("http://", "").split("/")[0]
    clean_domain = normalize_string(domain)
    
    for partner in partners:
        p_name = partner.get('partner_name', '')
        if not p_name: continue
        
        clean_partner = normalize_string(p_name)
        
        # Verifica se o nome limpo do parceiro está no domínio limpo
        # Ex: "casasbahia" in "www.casasbahia.com.br"
        if clean_partner in clean_domain:
            return True, p_name
            
    return False, None

# --- SESSION STATE ---
if "resultado_coach" not in st.session_state:
    st.session_state["resultado_coach"] = None
if "dados_vicio" not in st.session_state:
    st.session_state["dados_vicio"] = None
if "resultados_tavily" not in st.session_state:
    st.session_state["resultados_tavily"] = []

# --- CSS PARA DEIXAR BONITO (Opcional) ---
st.markdown("""
<style>
    /* Fundo geral e fontes */
    .stApp {
        background-color: #0E1117;
    }
    
    /* Estilo dos Cards de Métricas */
    div[data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #464B5C;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
        transition: transform 0.2s;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: scale(1.02);
        border-color: #FF4B4B;
    }

    /* Botão Principal */
    .stButton>button {
        width: 100%;
        border-radius: 25px;
        height: 3em;
        background: linear-gradient(90deg, #FF4B4B 0%, #FF914D 100%);
        color: white;
        font-weight: bold;
        border: none;
        box-shadow: 0px 5px 15px rgba(255, 75, 75, 0.4);
    }
    
    .stButton>button:hover {
        box-shadow: 0px 8px 20px rgba(255, 75, 75, 0.6);
        transform: translateY(-2px);
    }
    
    /* Títulos */
    h1 {
        text-align: center;
        background: -webkit-linear-gradient(#eee, #999);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Discurso do Coach */
    .coach-text {
        font-size: 24px !important;
        font-weight: bold;
        color: #FFD700; /* Dourado */
        background-color: rgba(255, 215, 0, 0.1);
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #FFD700;
        line-height: 1.5;
    }
    div[data-testid="stMetricValue"] > div {
        white-space: normal !important; /* Permite quebrar a linha */
        word-wrap: break-word !important; /* Quebra palavras longas */
        font-size: 1.8rem !important; /* Ajusta tamanho se necessário (padrão é grandão) */
        line-height: 1.2 !important;
    }
    /* Tooltip do Preço */
    div[data-testid="stMetricLabel"] label span {
        font-size: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURAÇÃO DAS APIS ---
# Tenta pegar dos secrets do Streamlit, senão pede input (pra não quebrar se rodar local sem config)
try:
    api_key_tavily = st.secrets["TAVILY_API_KEY"]
    api_key_groq = st.secrets["GROQ_API_KEY"] # Mudou aqui
except:
    st.warning("⚠️ Configuração de API não encontrada nos Secrets.")
    api_key_tavily = st.text_input("Tavily API Key", type="password")
    api_key_groq = st.text_input("Groq API Key", type="password")

# --- DICIONÁRIO DE VÍCIOS (MOEDAS) ---
MOEDAS = {
    "🍺 Cerveja (Heineken Long Neck)": {"preco": 6.50, "unidade": "garrafas", "verbo": "beber", "emoji_visual": "🍺"},
    "🍺 Ir no Barzinho": {"preco": 120, "unidade": "barzinhos", "verbo": "beber", "emoji_visual": "🍺"},
    "☕ Café Expresso (Padaria)": {"preco": 8.00, "unidade": "xícaras", "verbo": "tomar", "emoji_visual": "☕"},
    "🍔 Combo Fast Food": {"preco": 35.00, "unidade": "combos", "verbo": "comer", "emoji_visual": "🍔"},
    "🚬 Cigarro (Maço)": {"preco": 12.00, "unidade": "maços", "verbo": "fumar", "emoji_visual": "🚬"},
    "💅 Manicure/Salão": {"preco": 60.00, "unidade": "idas ao salão", "verbo": "fazer", "emoji_visual": "💅"},
    "🚗 Uber (Corrida Média)": {"preco": 20.00, "unidade": "viagens", "verbo": "pedir", "emoji_visual": "🚕"},
    "🍽 Jantar fora": {"preco": 250.00, "unidade": "jantares", "verbo": "comer", "emoji_visual": "🍽"},
    "🍽 Almoçar fora": {"preco": 200.00, "unidade": "almoços", "verbo": "comer", "emoji_visual": "🍽"},
    "🏃 Corrida de rua": {"preco": 100.00, "unidade": "corridas", "verbo": "correr", "emoji_visual": "🏃"},
    "🛍 Compras compulsivas": {"preco": 75.00, "unidade": "compras", "verbo": "comprar", "emoji_visual": "🛍"},
    "🛍 Brusinha da shein": {"preco": 250.00, "unidade": "brusinhas", "verbo": "comprar", "emoji_visual": "🛍"},
    "🛍 Carrinho da amazon": {"preco": 200.00, "unidade": "carrinhos", "verbo": "comprar", "emoji_visual": "🛍"},
    "🛍 Carrinho da shopee": {"preco": 150.00, "unidade": "carrinhos", "verbo": "comprar", "emoji_visual": "🛍"},
    "🎮 Lootbox no joguinho": {"preco": 69.90, "unidade": "lootboxes", "verbo": "comprar", "emoji_visual": "🛍"},
}

# --- SISTEMA DE CACHE (JSON) ---
CACHE_FILE = "dream_cache.json"

def get_price_from_tavily(produto):
    # 1. Verifica Cache
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        if produto.lower() in cache:
            return cache[produto.lower()]
    
    # 2. Busca na Tavily se não tiver no cache
    if not api_key_tavily:
        return None, "Sem API Key"
    
    client = TavilyClient(api_key=api_key_tavily)
    # Busca mais específica para e-commerce
    query = f"comprar {produto} oferta loja online brasil"
    response = client.search(query, search_depth="basic")
    
    # Aqui usamos uma lógica simples: pegamos o conteúdo e pedimos pra IA extrair o preço
    # Para economizar tokens e ser rápido no hackathon, vamos retornar o texto cru da busca
    # e deixar o GPT extrair e já fazer o coach no mesmo prompt.
    # Filtra resultados que parecem blogs/notícias
    filtered_results = []
    ignore_terms = ["blog", "noticia", "artigo", "review", "news", "techtudo", "canaltech"]
    
    for res in response['results']:
        url = res['url'].lower()
        if not any(term in url for term in ignore_terms):
            filtered_results.append(res)
            
    # Se filtrou tudo, usa o original
    if not filtered_results:
        filtered_results = response['results']

    # Retorna objeto completo com resultados para pegar links
    return {
        "content": response['results'][0]['content'], # Mantém o conteúdo do top 1 para o LLM
        "results": filtered_results
    }

# --- INTERFACE ---
st.title("🚀 DreamSwap AI")
st.markdown("### Transforme seus Vícios em Conquistas! 🦁")
st.markdown("Descubra o que você precisa **sacrificar** para atingir seu sonho.")

col1, col2 = st.columns(2)

with col1:
    produto = st.text_input("💎 Qual é o seu Sonho?", "Playstation 5")

with col2:
    vicio_key = st.selectbox("🛑 Qual seu Vício de Estimação?", list(MOEDAS.keys()))
    dados_vicio = MOEDAS[vicio_key]

if st.button("🔥 ATIVAR MODO COACH 🔥"):
    if not api_key_groq or not api_key_tavily:
        st.error("Preencha as chaves de API primeiro!")
    else:
       # --- AQUI ESTÁ O TRUQUE DE LAZY LOADING VISUAL ---
        placeholder = st.empty() # Cria um espaço vazio
        
        with placeholder.container():
            c1, c2, c3 = st.columns([1,2,1])
            with c2:
                # Mostra animação enquanto processa
                if lottie_loading:
                    st_lottie(lottie_loading, height=200, key="loading")
                else:
                    st.spinner("Processando...")
                st.markdown("<h3 style='text-align: center;'>Consultando os astros financeiros...</h3>", unsafe_allow_html=True)
                # 1. Buscar Contexto (RAG)
                dados_busca = get_price_from_tavily(produto)
                
                # Compatibilidade com cache antigo (se for string, transforma em dict fake)
                if isinstance(dados_busca, str):
                     dados_busca = {"content": dados_busca, "results": []}
                elif dados_busca is None: # Erro
                     dados_busca = {"content": "", "results": []}

                contexto_busca = dados_busca['content']
                resultados_tavily = dados_busca.get('results', [])
                
                # 2. Chamar o Coach (USANDO GROQ)
                client_groq = OpenAI(
                    api_key=api_key_groq,
                    base_url="https://api.groq.com/openai/v1"
                )
                
                prompt = f"""
                ATUE COMO UM COACH FINANCEIRO DE ALTA PERFORMANCE (ESTILO PABLO MARÇAL / TONY ROBBINS).
                VOCÊ ESTÁ MUITO BRAVO COM O USUÁRIO POR ELE GASTAR DINHEIRO COM BESTEIRA.
                
                DADOS REAIS DA BUSCA NA WEB SOBRE O PRODUTO '{produto}':
                "{contexto_busca}"
                
                DADOS DO VÍCIO DO USUÁRIO:
                Item: {vicio_key}
                Preço Unitário: R$ {dados_vicio['preco']}
                Verbo: {dados_vicio['verbo']}
                
                MISSÃO:
                1. Analise o texto da busca e encontre o preço do {produto}.
                2. Calcule quantos itens do vício são necessários para comprar o produto.
                3. Responda APENAS NO FORMATO JSON ABAIXO.
                
                REGRAS PARA O DISCURSO DO COACH ("discurso_coach"):
                - NÃO MENCIONE O PREÇO EM REAIS DO PRODUTO (R$ XX.XXX). É PROIBIDO.
                - O PREÇO DEVE SER SEMPRE EM REAIS (BRL). Se encontrar em Dólar, converta (1 USD = R$ 6,00).
                - Priorize lojas brasileiras (Amazon BR, Mercado Livre, Magalu).
                - Fale APENAS na quantidade de vícios (Ex: "Esse iPhone custa 371 Combos!").
                - A lógica deve ser de TROCA/SACRIFÍCIO: "Deixe de {dados_vicio['verbo']} {vicio_key} para conquistar seu sonho".
                - Pode variar as interações do discurso para que seja mais como um coach.
                - Seja agressivo: "Você está comendo seu futuro!", "Pare de queimar dinheiro!", "Abra mão hoje para ter amanhã!".
                - NÃO USE EMOJIS no texto do discurso (para leitura limpa).
                - MÁXIMO DE 500 CARACTERES.
                
                FORMATO DE RESPOSTA (JSON):
                {{
                    "preco_produto": 00.00,
                    "qtd_vicio": 00,
                    "discurso_coach": "Texto motivacional curto, agressivo e sem falar o preço em reais."
                }}
                """
                
                try:
                    completion = client_groq.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "Você é um assistente que responde APENAS em JSON válido."},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"}
                    )

                    placeholder.empty() # Limpa a animação
                    
                    # SALVA NO SESSION STATE
                    st.session_state["resultado_coach"] = json.loads(completion.choices[0].message.content)
                    st.session_state["dados_vicio"] = dados_vicio
                    st.session_state["resultados_tavily"] = resultados_tavily
                    
                    # ATUALIZA HISTÓRICO GLOBAL
                    novo_registro = {
                        'sonho': produto,
                        'vicio': vicio_key,
                        'coach': st.session_state["resultado_coach"]['discurso_coach']
                    }
                    historico.insert(0, novo_registro)
                    
                except Exception as e:
                    st.error(f"O coach teve um burnout (Erro): {e}")

# --- EXIBIÇÃO DOS RESULTADOS (PERSISTENTE) ---
if st.session_state["resultado_coach"]:
    resultado = st.session_state["resultado_coach"]
    dados_vicio_saved = st.session_state["dados_vicio"]
    resultados_tavily = st.session_state.get("resultados_tavily", [])

    # Título do Resultado
    st.markdown("## 🦁 O Veredito do Coach")
    
    # Container estilizado visualmente
    with st.container():
        c1, c2, c3 = st.columns(3)
        c1.metric("Preço do Sonho", f"R$ {resultado['preco_produto']:,.2f}", help="Valor estimado encontrado na web")
        c2.metric("Preço do Vício", f"R$ {dados_vicio_saved['preco']:,.2f}")
        c3.metric("Sacrifício Necessário", f"{int(resultado['qtd_vicio'])} {dados_vicio_saved['unidade']}")
    
    st.divider()
    
    st.markdown(f'<div class="coach-text">🗣️ "{resultado["discurso_coach"]}"</div>', unsafe_allow_html=True)
    
    # --- ONDE COMPRAR (MÉLIUZ) ---
    if resultados_tavily:
        st.divider()
        st.subheader("🛍️ Onde Comprar (com Cashback?)")
        st.caption("Encontramos essas lojas. Se tiver o selo roxo, tem Cashback no Méliuz!")
        
        cols = st.columns(3)
        for i, item in enumerate(resultados_tavily[:3]): # Pega os 3 primeiros
            with cols[i]:
                has_cashback, partner_name = check_meliuz_cashback(item['url'], meliuz_partners)
                
                # Cardzinho da Loja
                st.markdown(f"**{item['title'][:50]}...**")
                st.markdown(f"🔗 [Acessar Loja]({item['url']})")
                
                if has_cashback:
                    st.success(f"🟣 **{partner_name}** tem Cashback!")
                else:
                    st.info("⚪ Sem cashback identificado")
    
    # --- VISUALIZAÇÃO DE CHOQUE (EMOJI WALL) ---
    st.divider()
    st.subheader("🧱 A Muralha do Desperdício")
    st.caption(f"Visualize o tamanho do sacrifício: Aqui estão os {int(resultado['qtd_vicio'])} itens que te separam do seu sonho.")
    
    qtd_visual = int(resultado['qtd_vicio'])
    emoji_icon = dados_vicio_saved['emoji_visual']
    
    # Limitador de segurança
    limite_tela = 800 
    
    if qtd_visual <= limite_tela:
        st.write(f"{(emoji_icon + ' ') * qtd_visual}")
    else:
        st.write(f"{(emoji_icon + ' ') * limite_tela}")
        st.warning(f"... e mais {qtd_visual - limite_tela} {emoji_icon} que não cabem na tela do seu computador! 😱")
    
    # --- ÁUDIO DO COACH (Versão Grátis - gTTS) ---
    st.divider()
    st.write("🔊 **Ouça o sermão do Coach:**")
    
    col_audio_1, col_audio_2 = st.columns(2)
    
    with col_audio_1:
        if st.button("🔊 Ouvir (Grátis - gTTS)"):
            try:
                tts = gTTS(text=resultado['discurso_coach'], lang='pt', slow=False)
                audio_fp = BytesIO()
                tts.write_to_fp(audio_fp)
                st.audio(audio_fp, format='audio/mp3', autoplay=True)
            except Exception as e:
                st.error(f"Erro ao gerar áudio: {e}")

    with col_audio_2:
        if st.button("🎙️ Gerar Áudio com ElevenLabs"):
            try:
                api_key_eleven = st.secrets["ELEVENLABS_API_KEY"]
                client_eleven = ElevenLabs(api_key=api_key_eleven)
                
                audio_generator = client_eleven.text_to_speech.convert(
                    text=resultado['discurso_coach'],
                    voice_id="JBFqnCBsd6RMkjVDRZzb", # George
                    model_id="eleven_multilingual_v2"
                )
                
                # Consumir o gerador para bytes
                audio_bytes = b"".join(audio_generator)
                
                st.audio(audio_bytes, format="audio/mp3", autoplay=True)
                
            except Exception as e:
                st.error(f"Erro ElevenLabs: {e}. Verifique a chave ou créditos.")

    st.balloons()

# --- SIDEBAR (MURAL PÚBLICO) ---
with st.sidebar:
    st.title("👀 Espiando os Vizinhos")
    st.caption("Veja o que a galera está sacrificando:")
    st.divider()
    
    # Mostra os 5 últimos
    for item in historico[:5]:
        st.markdown(f"**Sonho:** {item['sonho']}")
        st.markdown(f"**Vício:** {item['vicio']}")
        st.markdown(f"_{item['coach']}_")
        st.divider()

# Rodapé
st.markdown("---")
st.caption("Desenvolvido para o Desafio AI First BF 2025 | Powered by Groq & Tavily")