# chatbot.py
import os
import logging
import time
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from bot_faculdade import Atendimento, consultar_ia, consultar_curso_especifico, consultar_info_curso

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# memória de atendimentos ativos
atendimentos = {}

# ---------- teclados reutilizáveis ----------
KB_INITIAL = ReplyKeyboardMarkup(
    [[KeyboardButton("Sou aluno"), KeyboardButton("Não sou aluno")]],
    resize_keyboard=True,
    one_time_keyboard=False
)

KB_STUDENT_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("Financeiro"), KeyboardButton("Secretaria")],
        [KeyboardButton("Documentos"), KeyboardButton("Informações do curso")],
        [KeyboardButton("Falar com atendente"), KeyboardButton("Cancelar")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

KB_FINANCEIRO = ReplyKeyboardMarkup(
    [
        [KeyboardButton("Ver boletos"), KeyboardButton("Segunda via")],
        [KeyboardButton("Acordo / Renegociação"), KeyboardButton("Consultar pagamentos")],
        [KeyboardButton("Voltar"), KeyboardButton("Falar com atendente")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

KB_SECRETARIA = ReplyKeyboardMarkup(
    [
        [KeyboardButton("Reposição / Recuperação"), KeyboardButton("Calendário acadêmico")],
        [KeyboardButton("Horário das aulas"), KeyboardButton("Troca de curso")],
        [KeyboardButton("Voltar"), KeyboardButton("Falar com atendente")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

KB_DOCUMENTOS = ReplyKeyboardMarkup(
    [
        [KeyboardButton("Declaração de matrícula"), KeyboardButton("Atestado de frequência")],
        [KeyboardButton("Histórico parcial"), KeyboardButton("Solicitar diploma")],
        [KeyboardButton("Voltar"), KeyboardButton("Falar com atendente")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

KB_CURSOS = ReplyKeyboardMarkup(
    [
        [KeyboardButton("Listar todos os cursos"), KeyboardButton("Grade curricular")],
        [KeyboardButton("Disciplinas por semestre"), KeyboardButton("Voltar")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

KB_VISITOR = ReplyKeyboardMarkup(
    [
        [KeyboardButton("Ver cursos"), KeyboardButton("Ver valores")],
        [KeyboardButton("Documentos para matrícula"), KeyboardButton("Como se inscrever")],
        [KeyboardButton("Falar com consultor"), KeyboardButton("Cancelar")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# ---------- utilitário de encerramento ----------
async def encerrar_e_limpar_atendimento(update: Update, atendimento: Atendimento, user_id: int):
    try:
        caminho = atendimento.gerar_csv()
        if caminho != "erro_ao_gerar_csv":
            await update.message.reply_text(f"📁 Atendimento registrado em:\n{caminho}")
        await update.message.reply_text("✅ Atendimento finalizado. Digite /start para iniciar outro atendimento.")
        atendimento.encerrado = True
        if user_id in atendimentos:
            del atendimentos[user_id]
    except Exception as e:
        logger.error(f"Erro ao encerrar atendimento: {e}")
        await update.message.reply_text("✅ Atendimento finalizado. Digite /start para iniciar outro atendimento.")

# ---------- /start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.message.from_user.id
        # Limpar sessão anterior se existir
        if user in atendimentos:
            del atendimentos[user]
        
        atendimentos[user] = Atendimento(user)
        # etapa 10 = perguntando se é aluno
        atendimentos[user].etapa = 10
        await update.message.reply_text(
            "Olá! 👋 Seja bem-vindo ao atendimento virtual da UniFECAF.\n"
            "Antes de começarmos: você é aluno da instituição?",
            reply_markup=KB_INITIAL
        )
    except Exception as e:
        logger.error(f"Erro no comando start: {e}")
        await update.message.reply_text("Erro ao iniciar atendimento. Tente novamente.")

# ---------- COMANDO /cursos ----------
async def cursos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando específico para consulta de cursos"""
    try:
        user = update.message.from_user.id
        
        # Se não tiver sessão ativa, criar uma temporária
        if user not in atendimentos:
            atendimentos[user] = Atendimento(user)
            atendimentos[user].etapa = 60  # Modo consulta de cursos
        
        if context.args:
            # Se o usuário passou argumentos, fazer busca direta
            busca = " ".join(context.args)
            resposta = consultar_curso_especifico(busca)
            await update.message.reply_text(resposta)
        else:
            # Mostrar menu de opções de cursos
            atendimentos[user].etapa = 60
            await update.message.reply_text(
                "🎓 **Consulta de Cursos UniFECAF**\n\n"
                "Escolha uma opção ou digite o nome de um curso específico:",
                reply_markup=KB_CURSOS,
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Erro no comando /cursos: {e}")
        await update.message.reply_text("Erro ao consultar cursos. Tente novamente.")

# ---------- mensagem principal ----------
async def mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user.id
    texto_raw = update.message.text.strip()
    
    # Verificar se a mensagem está vazia
    if not texto_raw:
        await update.message.reply_text("Por favor, digite uma mensagem válida.")
        return

    texto = texto_raw.lower()

    # Verificar timeout de sessão (30 minutos)
    if user in atendimentos:
        tempo_sessao = time.time() - atendimentos[user].inicio.timestamp()
        if tempo_sessao > 1800:  # 30 minutos
            await update.message.reply_text("⏰ Sessão expirada. Digite /start para reiniciar.")
            del atendimentos[user]
            return

    # se não tiver sessão ativa ou já encerrado, força start
    if user not in atendimentos or atendimentos[user].encerrado:
        if not texto.startswith("/"):
            await update.message.reply_text("Digite /start para iniciar o atendimento.")
        return await start(update, context)

    atendimento = atendimentos[user]

    try:
        # ---------- ETAPA 10: aluno ou visitante ----------
        if atendimento.etapa == 10:
            if texto == "sou aluno":
                atendimento.registrar("cliente_tipo", "aluno")
                atendimento.etapa = 12  # pedir RA
                return await update.message.reply_text("Perfeito — por favor, informe seu RA (apenas números):")
            elif texto == "não sou aluno" or texto == "nao sou aluno":
                atendimento.registrar("cliente_tipo", "visitante")
                atendimento.etapa = 70  # visitante menu
                return await update.message.reply_text(
                    "Perfeito — como posso te ajudar hoje?", reply_markup=KB_VISITOR
                )
            else:
                return await update.message.reply_text("Por favor escolha: 'Sou aluno' ou 'Não sou aluno'.")

        # ---------- ETAPA 12: receber RA ----------
        if atendimento.etapa == 12:
            # Validação básica do RA
            if not texto_raw.isdigit() or len(texto_raw) < 3:
                return await update.message.reply_text("Por favor, digite um RA válido (apenas números, pelo menos 3 dígitos):")
            
            atendimento.registrar("ra", texto_raw)
            atendimento.etapa = 13
            return await update.message.reply_text("Obrigado. Qual é o seu curso? (digite o nome ou abreviação)")

        # ---------- ETAPA 13: receber curso ----------
        if atendimento.etapa == 13:
            atendimento.registrar("curso", texto_raw)
            atendimento.etapa = 20  # student menu
            return await update.message.reply_text(
                "O que deseja fazer hoje? Escolha uma opção:", reply_markup=KB_STUDENT_MENU
            )

        # ---------- ETAPA 20: menu do aluno ----------
        if atendimento.etapa == 20:
            if texto == "financeiro":
                atendimento.registrar("setor", "financeiro")
                atendimento.etapa = 30
                return await update.message.reply_text("Você escolheu Financeiro. O que deseja?", reply_markup=KB_FINANCEIRO)
            if texto == "secretaria":
                atendimento.registrar("setor", "secretaria")
                atendimento.etapa = 40
                return await update.message.reply_text("Você escolheu Secretaria. O que deseja?", reply_markup=KB_SECRETARIA)
            if texto == "documentos":
                atendimento.registrar("setor", "documentos")
                atendimento.etapa = 50
                return await update.message.reply_text("Você escolheu Documentos. O que deseja?", reply_markup=KB_DOCUMENTOS)
            if texto == "informações do curso" or texto == "informacoes do curso":
                atendimento.registrar("setor", "info_curso")
                atendimento.etapa = 60
                return await update.message.reply_text(
                    "🎓 **Consulta de Informações do Curso**\n\n"
                    "Você pode:\n"
                    "- Digitar o nome de um curso específico\n"  
                    "- Perguntar sobre disciplinas\n"
                    "- Usar os botões abaixo para navegar",
                    reply_markup=KB_CURSOS,
                    parse_mode='Markdown'
                )
            if texto == "falar com atendente":
                # direciona para atendimento humano
                atendimento.registrar("solicitacao", "falar_com_atendente")
                await update.message.reply_text(
                    "👥 **Encaminhando para Atendimento Humano**\n\n"
                    "📧 **E-mail:** atendimento@unifecaf.edu.br\n"
                    "📋 **Inclua em seu e-mail:**\n"
                    "• Seu RA: " + atendimento.registros.get('ra', 'Não informado') + "\n"
                    "• Seu curso: " + atendimento.registros.get('curso', 'Não informado') + "\n"
                    "• Descrição detalhada do seu pedido\n\n"
                    "⏰ **Prazo de retorno:** 24h úteis"
                )
                return await encerrar_e_limpar_atendimento(update, atendimento, user)
            if texto == "cancelar":
                await update.message.reply_text("Atendimento cancelado pelo usuário.")
                return await encerrar_e_limpar_atendimento(update, atendimento, user)

            # qualquer outra entrada: considerar texto livre -> usar IA para interpretar
            contexto = f"Aluno: RA {atendimento.registros.get('ra')}, Curso: {atendimento.registros.get('curso')}"
            prompt = f"O usuário (aluno) escreveu: '{texto_raw}'. {contexto}. Resuma em uma frase e responda de forma cortês, sugerindo as opções do menu."
            ia_resp = consultar_ia(prompt, contexto)
            atendimento.registrar("ia_interpretacao_menu", ia_resp)
            return await update.message.reply_text(f"{ia_resp}\n\nSe preferir, escolha uma opção no menu.", reply_markup=KB_STUDENT_MENU)

        # ---------- CONSULTA DE CURSOS (etapa 60) ----------
        if atendimento.etapa == 60:
            if texto == "listar todos os cursos":
                resposta = consultar_info_curso()
                await update.message.reply_text(resposta)
                return await encerrar_e_limpar_atendimento(update, atendimento, user)
            
            elif texto == "grade curricular":
                atendimento.registrar("consulta_curso", "grade_geral")
                await update.message.reply_text("Digite o nome do curso que deseja ver a grade curricular completa:")
                return
            
            elif texto == "disciplinas por semestre":
                atendimento.registrar("consulta_curso", "disciplinas_semestre")
                await update.message.reply_text("Digite o curso e semestre (ex: 'Análise e Desenvolvimento de Sistemas 1º semestre'):")
                return
            
            elif texto == "voltar":
                atendimento.etapa = 20
                return await update.message.reply_text("Voltando ao menu principal.", reply_markup=KB_STUDENT_MENU)
            
            else:
                # Consulta livre sobre cursos - usar a função especializada
                resposta = consultar_curso_especifico(texto_raw)
                atendimento.registrar("consulta_curso_livre", texto_raw)
                atendimento.registrar("resposta_curso", resposta)
                
                if len(resposta) > 4000:
                    # Dividir resposta longa
                    partes = [resposta[i:i+4000] for i in range(0, len(resposta), 4000)]
                    for parte in partes:
                        await update.message.reply_text(parte)
                else:
                    await update.message.reply_text(resposta)
                
                # Oferecer continuar ou encerrar
                await update.message.reply_text(
                    "Deseja fazer outra consulta ou voltar ao menu principal?",
                    reply_markup=ReplyKeyboardMarkup(
                        [[KeyboardButton("Nova consulta"), KeyboardButton("Voltar ao menu")]],
                        resize_keyboard=True
                    )
                )
                atendimento.etapa = 61  # Aguardando decisão pós-consulta
                return

        # ---------- DECISÃO PÓS-CONSULTA (etapa 61) ----------
        if atendimento.etapa == 61:
            if texto == "nova consulta" or texto == "outra consulta":
                atendimento.etapa = 60
                return await update.message.reply_text(
                    "🎓 Digite sua próxima consulta sobre cursos:",
                    reply_markup=KB_CURSOS
                )
            elif texto == "voltar ao menu" or texto == "voltar":
                atendimento.etapa = 20
                return await update.message.reply_text("Voltando ao menu principal.", reply_markup=KB_STUDENT_MENU)
            else:
                # Tratar como nova consulta
                resposta = consultar_curso_especifico(texto_raw)
                await update.message.reply_text(resposta)
                await update.message.reply_text(
                    "Deseja fazer outra consulta ou voltar ao menu principal?",
                    reply_markup=ReplyKeyboardMarkup(
                        [[KeyboardButton("Nova consulta"), KeyboardButton("Voltar ao menu")]],
                        resize_keyboard=True
                    )
                )
                return

        # ---------- FINANCEIRO (etapa 30 e 31) ----------
        if atendimento.etapa == 30:
            if texto in ["ver boletos", "ver boletos"]:
                atendimento.registrar("financeiro_acao", "ver_boletos")
                atendimento.etapa = 31
                return await update.message.reply_text("Deseja alguma observação específica sobre os boletos? Descreva resumidamente (ou digite 'não'):")
            if texto == "segunda via":
                atendimento.registrar("financeiro_acao", "segunda_via")
                atendimento.etapa = 31
                return await update.message.reply_text("Informe, se quiser, o mês/competência da segunda via (ou digite 'não'):")
            if texto == "acordo / renegociação" or texto == "acordo / renegociacao" or texto == "acordo":
                atendimento.registrar("financeiro_acao", "acordo")
                atendimento.etapa = 31
                return await update.message.reply_text("Descreva a proposta de acordo (valor/parcelas) ou digite 'não':")
            if texto == "consultar pagamentos":
                atendimento.registrar("financeiro_acao", "consultar_pagamentos")
                atendimento.etapa = 31
                return await update.message.reply_text("Se quiser, escreva detalhes (período) ou digite 'não':")
            if texto == "voltar":
                atendimento.etapa = 20
                return await update.message.reply_text("Voltando ao menu principal.", reply_markup=KB_STUDENT_MENU)
            if texto == "falar com atendente":
                atendimento.registrar("solicitacao", "falar_com_atendente_financeiro")
                await update.message.reply_text(
                    "👥 **Encaminhando para Financeiro**\n\n"
                    "📧 **E-mail:** financeiro@unifecaf.edu.br\n"
                    "📋 **Inclua em seu e-mail:**\n"
                    "• Seu RA: " + atendimento.registros.get('ra', 'Não informado') + "\n"
                    "• Seu curso: " + atendimento.registros.get('curso', 'Não informado') + "\n"
                    "• Descrição detalhada da solicitação financeira\n\n"
                    "⏰ **Prazo de retorno:** 24h úteis"
                )
                return await encerrar_e_limpar_atendimento(update, atendimento, user)

            # entrada livre: IA tenta entender
            contexto = f"Aluno: RA {atendimento.registros.get('ra')}, Curso: {atendimento.registros.get('curso')}, Setor: Financeiro"
            prompt = f"Usuário pediu algo no Financeiro: '{texto_raw}'. {contexto}. Resuma a solicitação e explique os próximos passos possíveis em linguagem natural."
            ia_resp = consultar_ia(prompt, contexto)
            atendimento.registrar("ia_financeiro_interpretacao", ia_resp)
            return await update.message.reply_text(f"{ia_resp}\n\nSe deseja, escolha uma opção no menu financeiro.", reply_markup=KB_FINANCEIRO)

        # etapa 31: recebendo descrição para ação financeira
        if atendimento.etapa == 31:
            detalhe = texto_raw
            atendimento.registrar("financeiro_detalhe", detalhe)
            
            # CONTEXTO COMPLETO PARA IA
            contexto = f"""
            DADOS DO ALUNO:
            • RA: {atendimento.registros.get('ra', 'Não informado')}
            • Curso: {atendimento.registros.get('curso', 'Não informado')}
            • Ação Financeira: {atendimento.registros.get('financeiro_acao')}
            • Detalhes: {detalhe}
            """
            
            prompt = f"Processar solicitação financeira: '{detalhe}'. Forneça confirmação e próximos passos."
            ia_resp = consultar_ia(prompt, contexto)
            atendimento.registrar("ia_financeiro_resposta", ia_resp)
            await update.message.reply_text(ia_resp)
            return await encerrar_e_limpar_atendimento(update, atendimento, user)

        # ---------- SECRETARIA (etapa 40 e 41) ----------
        if atendimento.etapa == 40:
            if texto in ["reposição / recuperação", "reposição", "recuperação", "recuperacao"]:
                atendimento.registrar("secretaria_acao", "recuperacao")
                atendimento.etapa = 41
                return await update.message.reply_text("Qual a disciplina / período relacionada à recuperação? Descreva:")
            if texto == "calendário acadêmico" or texto == "calendario acadêmico" or texto == "calendario academico":
                atendimento.registrar("secretaria_acao", "calendario")
                await update.message.reply_text("📅 **Calendário Acadêmico**\n\nVocê pode acessar o calendário acadêmico atualizado no portal institucional da UniFECAF.")
                return await encerrar_e_limpar_atendimento(update, atendimento, user)
            if texto == "horário das aulas" or texto == "horario das aulas":
                atendimento.registrar("secretaria_acao", "horario")
                atendimento.etapa = 41
                return await update.message.reply_text("Informe, por favor, qual curso/turno (ex: Tarde, Noite) para buscarmos o horário:")
            if texto == "troca de curso":
                atendimento.registrar("secretaria_acao", "troca_curso")
                atendimento.etapa = 41
                return await update.message.reply_text("Para qual curso deseja trocar? Informe o nome do curso:")
            if texto == "voltar":
                atendimento.etapa = 20
                return await update.message.reply_text("Voltando ao menu principal.", reply_markup=KB_STUDENT_MENU)
            if texto == "falar com atendente":
                atendimento.registrar("solicitacao", "falar_com_atendente_secretaria")
                await update.message.reply_text(
                    "👥 **Encaminhando para Secretaria**\n\n"
                    "📧 **E-mail:** secretaria@unifecaf.edu.br\n"
                    "📋 **Inclua em seu e-mail:**\n"
                    "• Seu RA: " + atendimento.registros.get('ra', 'Não informado') + "\n"
                    "• Seu curso: " + atendimento.registros.get('curso', 'Não informado') + "\n"
                    "• Descrição detalhada da solicitação\n\n"
                    "⏰ **Prazo de retorno:** 48h úteis"
                )
                return await encerrar_e_limpar_atendimento(update, atendimento, user)

            # livre -> IA interpreta
            contexto = f"Aluno: RA {atendimento.registros.get('ra')}, Curso: {atendimento.registros.get('curso')}, Setor: Secretaria"
            prompt = f"Solicitação para Secretaria: '{texto_raw}'. {contexto}. Explique em poucas palavras o que pode ser feito pelo bot e sugira opções."
            ia_resp = consultar_ia(prompt, contexto)
            atendimento.registrar("ia_secretaria_interpretacao", ia_resp)
            return await update.message.reply_text(f"{ia_resp}\n\nEscolha uma opção no menu da secretaria.", reply_markup=KB_SECRETARIA)

        if atendimento.etapa == 41:
            detalhe = texto_raw
            atendimento.registrar("secretaria_detalhe", detalhe)
            
            # CONTEXTO COMPLETO PARA IA
            contexto = f"""
            DADOS DO ALUNO:
            • RA: {atendimento.registros.get('ra', 'Não informado')}
            • Curso: {atendimento.registros.get('curso', 'Não informado')}
            • Ação Secretaria: {atendimento.registros.get('secretaria_acao')}
            • Detalhes: {detalhe}
            """
            
            prompt = f"Processar solicitação da secretaria: '{detalhe}'. Forneça confirmação e próximos passos."
            ia_resp = consultar_ia(prompt, contexto)
            atendimento.registrar("ia_secretaria_resposta", ia_resp)
            await update.message.reply_text(ia_resp)
            return await encerrar_e_limpar_atendimento(update, atendimento, user)

        # ---------- DOCUMENTOS (etapa 50 e 51) ----------
        if atendimento.etapa == 50:
            if texto in ["declaração de matrícula", "declaracao de matrícula", "declaração"]:
                atendimento.registrar("documento_solicitado", "declaracao_matricula")
                atendimento.etapa = 51
                return await update.message.reply_text("Deseja receber por e-mail em PDF ou retirar na secretaria? (digite 'email' ou 'retirar')")
            if texto in ["atestado de frequência", "atestado"]:
                atendimento.registrar("documento_solicitado", "atestado_frequencia")
                atendimento.etapa = 51
                return await update.message.reply_text("Deseja receber por e-mail em PDF ou retirar na secretaria? (digite 'email' ou 'retirar')")
            if texto in ["histórico parcial", "historico parcial", "histórico"]:
                atendimento.registrar("documento_solicitado", "historico_parcial")
                atendimento.etapa = 51
                return await update.message.reply_text("Deseja receber por e-mail em PDF ou retirar na secretaria? (digite 'email' ou 'retirar')")
            if texto == "solicitar diploma" or texto == "solicitar diploma":
                atendimento.registrar("documento_solicitado", "diploma")
                atendimento.etapa = 51
                return await update.message.reply_text("Solicitação de diploma iniciada. Deseja instruções por e-mail? (digite 'sim' ou 'não')")
            if texto == "voltar":
                atendimento.etapa = 20
                return await update.message.reply_text("Voltando ao menu principal.", reply_markup=KB_STUDENT_MENU)
            if texto == "falar com atendente":
                atendimento.registrar("solicitacao", "falar_com_atendente_documentos")
                await update.message.reply_text(
                    "👥 **Encaminhando para Documentos**\n\n"
                    "📧 **E-mail:** documentos@unifecaf.edu.br\n"
                    "📋 **Inclua em seu e-mail:**\n"
                    "• Seu RA: " + atendimento.registros.get('ra', 'Não informado') + "\n"
                    "• Seu curso: " + atendimento.registros.get('curso', 'Não informado') + "\n"
                    "• Documento(s) solicitado(s)\n"
                    "• Preferência de recebimento\n\n"
                    "⏰ **Prazo de retorno:** 24h úteis"
                )
                return await encerrar_e_limpar_atendimento(update, atendimento, user)

            # livre -> IA interpreta
            contexto = f"Aluno: RA {atendimento.registros.get('ra')}, Curso: {atendimento.registros.get('curso')}, Setor: Documentos"
            prompt = f"Solicitação de documento: '{texto_raw}'. {contexto}. Resuma e indique opções (email/retirar/voltar)."
            ia_resp = consultar_ia(prompt, contexto)
            atendimento.registrar("ia_documentos_interpretacao", ia_resp)
            return await update.message.reply_text(f"{ia_resp}\n\nEscolha uma opção no menu de documentos.", reply_markup=KB_DOCUMENTOS)

        if atendimento.etapa == 51:
            escolha = texto_raw.lower()
            atendimento.registrar("documento_preferencia", escolha)
            
            # CONTEXTO COMPLETO PARA IA
            contexto = f"""
            DADOS DO ALUNO:
            • RA: {atendimento.registros.get('ra', 'Não informado')}
            • Curso: {atendimento.registros.get('curso', 'Não informado')}
            • Documento: {atendimento.registros.get('documento_solicitado')}
            • Preferência: {escolha}
            """
            
            prompt = f"Confirmar solicitação de documento com preferência: '{escolha}'. Forneça confirmação e próximos passos."
            ia_resp = consultar_ia(prompt, contexto)
            atendimento.registrar("ia_documentos_resposta", ia_resp)
            await update.message.reply_text(ia_resp)
            return await encerrar_e_limpar_atendimento(update, atendimento, user)

        # ---------- VISITANTE (etapa 70) ----------
        if atendimento.etapa == 70:
            if texto == "ver cursos":
                atendimento.registrar("visitante_acao", "ver_cursos")
                # Agora usa a consulta real do CSV
                resposta = consultar_info_curso()
                atendimento.registrar("ia_visitante_cursos", resposta)
                await update.message.reply_text(resposta)
                return await encerrar_e_limpar_atendimento(update, atendimento, user)
            if texto == "ver valores":
                atendimento.registrar("visitante_acao", "ver_valores")
                prompt = "Explique brevemente como consultar valores de mensalidades e opções de bolsas/financiamento na UniFECAF."
                ia_resp = consultar_ia(prompt)
                atendimento.registrar("ia_visitante_valores", ia_resp)
                await update.message.reply_text(ia_resp)
                return await encerrar_e_limpar_atendimento(update, atendimento, user)
            if texto == "documentos para matrícula":
                atendimento.registrar("visitante_acao", "documentos_matricula")
                prompt = "Liste os documentos necessários para matrícula de graduação (RG, CPF, comprovante, histórico, etc.)"
                ia_resp = consultar_ia(prompt)
                atendimento.registrar("ia_visitante_docs", ia_resp)
                await update.message.reply_text(ia_resp)
                return await encerrar_e_limpar_atendimento(update, atendimento, user)
            if texto == "como se inscrever":
                atendimento.registrar("visitante_acao", "como_inscrever")
                prompt = "Explique o processo de inscrição (link, provas, ENEM, contato) na UniFECAF de forma clara e convidativa."
                ia_resp = consultar_ia(prompt)
                atendimento.registrar("ia_visitante_inscricao", ia_resp)
                await update.message.reply_text(ia_resp)
                return await encerrar_e_limpar_atendimento(update, atendimento, user)
            if texto == "falar com consultor":
                atendimento.registrar("visitante_acao", "falar_consultor")
                await update.message.reply_text(
                    "👥 **Falar com Consultor**\n\n"
                    "📧 **E-mail:** comercial@unifecaf.edu.br\n"
                    "📞 **Telefone:** (11) 1234-5678\n"
                    "🕒 **Horário:** Segunda a sexta, 8h às 18h\n\n"
                    "Nossa equipe comercial terá prazer em tirar suas dúvidas!"
                )
                return await encerrar_e_limpar_atendimento(update, atendimento, user)
            if texto == "cancelar":
                await update.message.reply_text("Atendimento cancelado.")
                return await encerrar_e_limpar_atendimento(update, atendimento, user)

            # livre -> IA
            prompt = f"Visitante escreveu: '{texto_raw}'. Resuma a intenção e sugira as opções do menu de visitante."
            ia_resp = consultar_ia(prompt)
            atendimento.registrar("ia_visitante_interpretacao", ia_resp)
            return await update.message.reply_text(f"{ia_resp}\n\nEscolha uma opção ou digite 'Cancelar'.", reply_markup=KB_VISITOR)

        # ---------- CASO NÃO MAPEADO: direciona para e-mail e encerra ----------
        await update.message.reply_text(
            "❌ **Não foi possível processar automaticamente**\n\n"
            "👥 **Atendimento Humano**\n"
            "📧 **E-mail:** atendimento@unifecaf.edu.br\n"
            "📋 **Inclua:**\n"
            "• Seu RA: " + atendimento.registros.get('ra', 'Não informado') + "\n"
            "• Descrição detalhada do pedido\n\n"
            "⏰ **Retorno em até 24h úteis**"
        )
        return await encerrar_e_limpar_atendimento(update, atendimento, user)

    except Exception as e:
        logger.error(f"Erro no processamento da mensagem: {e}")
        await update.message.reply_text(
            "❌ **Erro interno do sistema**\n\n"
            "Desculpe, ocorreu um erro inesperado. "
            "Por favor, tente novamente ou entre em contato:\n"
            "📧 atendimento@unifecaf.edu.br"
        )

# ---------- MAIN ----------
def main():
    if not TELEGRAM_TOKEN:
        logging.error("TELEGRAM_TOKEN não encontrado no .env")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cursos", cursos_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensagem))

    print("🤖 BOT UNIFECAF RODANDO...")
    logger.info("Bot iniciado com sucesso!")
    app.run_polling()

if __name__ == "__main__":
    main()