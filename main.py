import os
import openai
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Carregar variáveis de ambiente
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Função de boas-vindas
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Eu sou o assistente virtual da UniFECAF.\n\n"
        "Posso te ajudar com dúvidas simples, como:\n"
        "- Acesso ao AVA ou Mentor 📚\n"
        "- Boletos 💰\n"
        "- Eletivas, estágios ou horas complementares 🎓\n\n"
        "Digite sua dúvida:"
    )

# Função para conversar com a API da OpenAI
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pergunta = update.message.text

    # Contexto do assistente
    prompt = f"""
    Você é um assistente virtual da faculdade UniFECAF.
    Responda de forma clara e educada a dúvidas simples de alunos.
    Exemplos de dúvidas:
    - Como acessar o AVA?
    - Onde vejo meus boletos?
    - Quantas horas complementares preciso fazer?
    Se não souber, oriente o aluno a procurar o setor correto.
    """

    try:
        resposta = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": pergunta}
            ],
            max_tokens=300,
            temperature=0.5
        )

        texto_resposta = resposta.choices[0].message.content.strip()
        await update.message.reply_text(texto_resposta)

    except Exception as e:
        await update.message.reply_text("⚠️ Ocorreu um erro ao processar sua solicitação.")
        print(f"Erro: {e}")

# Inicializar o bot
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🤖 Bot está rodando... Ctrl+C para parar.")
    app.run_polling()

if __name__ == "__main__":
    main()
