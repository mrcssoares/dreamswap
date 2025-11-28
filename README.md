# 🚀 DreamSwap AI

**Transforme seus Vícios em Conquistas!** 🦁

O **DreamSwap AI** é uma aplicação Streamlit desenvolvida para o Hackathon "DreamSwap". Ela ajuda os usuários a visualizarem o custo de seus sonhos em termos de seus "vícios" diários (café, fast food, etc.), oferecendo um choque de realidade com um Coach Financeiro agressivo e motivacional.

## ✨ Funcionalidades

-   **🔍 Busca de Preços em Tempo Real**: Utiliza a API da **Tavily** para encontrar o menor preço atual do produto desejado na web.
-   **🦁 Coach Financeiro AI**: Um assistente "casca grossa" (powered by **Groq / Llama 3.3**) que calcula quantos itens do seu vício você precisa sacrificar e te dá um sermão motivacional.
-   **🧱 Muralha do Desperdício**: Visualização gráfica impactante com emojis mostrando a quantidade física de itens que você está desperdiçando.
-   **🔊 Áudio do Coach**:
    -   **Grátis**: Leitura do sermão usando `gTTS` (Google Text-to-Speech).
    -   **Premium**: Voz ultra-realista usando **ElevenLabs** (Voz: George).

## 🛠️ Tecnologias

-   **Frontend**: [Streamlit](https://streamlit.io/)
-   **AI Model**: [Groq](https://groq.com/) (Llama 3.3-70b-versatile)
-   **Search**: [Tavily AI](https://tavily.com/)
-   **Audio**: [ElevenLabs](https://elevenlabs.io/) & [gTTS](https://pypi.org/project/gTTS/)

## 🚀 Como Rodar Localmente

1.  **Clone o repositório** (ou baixe os arquivos).

2.  **Instale as dependências**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure as Chaves de API**:
    -   Abra o arquivo `.streamlit/secrets.toml`.
    -   Preencha suas chaves:
        ```toml
        TAVILY_API_KEY = "sua-chave-tavily"
        GROQ_API_KEY = "sua-chave-groq"
        ELEVENLABS_API_KEY = "sua-chave-elevenlabs"
        ```

4.  **Execute a aplicação**:
    ```bash
    streamlit run app.py
    ```

## 📝 Estrutura do Projeto

-   `app.py`: Código principal da aplicação.
-   `requirements.txt`: Lista de dependências Python.
-   `.streamlit/secrets.toml`: Arquivo de configuração para chaves de API (NÃO COMITAR).
-   `dream_cache.json`: Cache local para evitar buscas repetidas (gerado automaticamente).

---
Desenvolvido para o Desafio AI First BF 2025.
