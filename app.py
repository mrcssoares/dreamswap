import streamlit as st
from tavily import TavilyClient
from openai import OpenAI
import json
import os
from datetime import datetime
from gtts import gTTS
from io import BytesIO
from elevenlabs.client import ElevenLabs

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="DreamSwap AI", page_icon="🚀", layout="centered")

# --- SESSION STATE ---
if "resultado_coach" not in st.session_state:
    st.session_state["resultado_coach"] = None
if "dados_vicio" not in st.session_state:
    st.session_state["dados_vicio"] = None

# --- CSS PARA DEIXAR BONITO (Opcional) ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
    }
    .big-font {
        font-size: 20px !important;
        font-weight: bold;
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
    "☕ Café Expresso (Padaria)": {"preco": 8.00, "unidade": "xícaras", "verbo": "tomar", "emoji_visual": "☕"},
    "🍔 Combo Fast Food": {"preco": 35.00, "unidade": "combos", "verbo": "comer", "emoji_visual": "🍔"},
    "🚬 Cigarro (Maço)": {"preco": 12.00, "unidade": "maços", "verbo": "fumar", "emoji_visual": "🚬"},
    "👶 Fralda (Pacote Econômico)": {"preco": 60.00, "unidade": "pacotes", "verbo": "trocar", "emoji_visual": "💩"},
    "💅 Manicure/Salão": {"preco": 45.00, "unidade": "idas ao salão", "verbo": "fazer", "emoji_visual": "💅"},
    "🚗 Uber (Corrida Média)": {"preco": 20.00, "unidade": "viagens", "verbo": "pedir", "emoji_visual": "🚕"},
    "🍽 Jantar fora": {"preco": 150.00, "unidade": "jantares", "verbo": "comer", "emoji_visual": "🍽"},
    "🏃 Corrida de rua": {"preco": 100.00, "unidade": "corridas", "verbo": "correr", "emoji_visual": "🏃"}
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
    response = client.search(f"Preço atual {produto} Brasil varejo", search_depth="basic")
    
    # Aqui usamos uma lógica simples: pegamos o conteúdo e pedimos pra IA extrair o preço
    # Para economizar tokens e ser rápido no hackathon, vamos retornar o texto cru da busca
    # e deixar o GPT extrair e já fazer o coach no mesmo prompt.
    contexto_busca = response['results'][0]['content']
    
    # Salva no cache (simplificado)
    # Nota: Em prod real, extrairíamos o valor numérico antes. 
    # Aqui vamos confiar que o GPT vai ler o texto da busca.
    return contexto_busca

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
        with st.spinner("Conectando com o Universo... 🧘‍♂️"):
            # 1. Buscar Contexto (RAG)
            contexto_busca = get_price_from_tavily(produto)
            
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
            - Fale APENAS na quantidade de vícios (Ex: "Esse iPhone custa 371 Combos!").
            - A lógica deve ser de TROCA/SACRIFÍCIO: "Deixe de {dados_vicio['verbo']} {vicio_key} para conquistar seu sonho".
            - Seja agressivo: "Você está comendo seu futuro!", "Pare de queimar dinheiro!".
            - NÃO USE EMOJIS no texto do discurso (para leitura limpa).
            - MÁXIMO DE 250 CARACTERES.
            
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
                
                # SALVA NO SESSION STATE
                st.session_state["resultado_coach"] = json.loads(completion.choices[0].message.content)
                st.session_state["dados_vicio"] = dados_vicio
                
            except Exception as e:
                st.error(f"O coach teve um burnout (Erro): {e}")

# --- EXIBIÇÃO DOS RESULTADOS (PERSISTENTE) ---
if st.session_state["resultado_coach"]:
    resultado = st.session_state["resultado_coach"]
    dados_vicio_saved = st.session_state["dados_vicio"]
    
    st.divider()
    
    # Métricas Gigantes
    c1, c2, c3 = st.columns(3)
    c1.metric("Preço do Sonho", f"R$ {resultado['preco_produto']:,.2f}")
    c2.metric("Preço do Vício", f"R$ {dados_vicio_saved['preco']:,.2f}")
    c3.metric("Sacrifício Necessário", f"{int(resultado['qtd_vicio'])} {dados_vicio_saved['unidade']}")
    
    st.success(f"### 🦁 COACH DIZ:")
    st.write(f"#### {resultado['discurso_coach']}")
    
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

# Rodapé
st.markdown("---")
st.caption("Desenvolvido para o Desafio AI First BF 2025 | Powered by Groq & Tavily")