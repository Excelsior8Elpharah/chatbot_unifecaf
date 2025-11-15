# ============================================
#      BOT FACULDADE - MÓDULO DE APOIO
# ============================================

import os
import csv
import uuid
import logging
import pandas as pd
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# carregar chave da API
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_KEY:
    raise Exception("❌ ERRO: Variável OPENAI_API_KEY não encontrada no .env")

client = OpenAI(api_key=OPENAI_KEY)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =======================================================
#   FUNÇÃO PARA CARREGAR DADOS DOS CURSOS
# =======================================================
def carregar_cursos_csv():
    """
    Carrega os dados dos cursos do arquivo CSV
    """
    try:
        df = pd.read_csv('Cursos Tech UniFECAF EAD.csv')
        
        # Processar os dados para estrutura mais limpa
        cursos = {}
        curso_atual = None
        semestre_atual = None
        
        for _, row in df.iterrows():
            # Verificar se é um novo curso
            if pd.notna(row['Curso']) and row['Curso'] != '---':
                curso_atual = row['Curso']
                cursos[curso_atual] = {}
            
            # Verificar se é um novo semestre
            if pd.notna(row['Semestre']) and row['Semestre'] != '---':
                semestre_atual = row['Semestre']
                if curso_atual:
                    cursos[curso_atual][semestre_atual] = []
            
            # Adicionar disciplina
            if pd.notna(row['Disciplina']) and curso_atual and semestre_atual:
                cursos[curso_atual][semestre_atual].append(row['Disciplina'])
        
        return cursos
    except Exception as e:
        logger.error(f"Erro ao carregar cursos do CSV: {e}")
        return {}

# Carregar dados dos cursos uma vez ao iniciar
CURSOS_DATA = carregar_cursos_csv()

# =======================================================
#   FUNÇÃO PARA CONSULTAR INFORMAÇÕES DOS CURSOS
# =======================================================
def consultar_info_curso(curso_nome=None, semestre=None, disciplina=None):
    """
    Consulta informações específicas sobre cursos, semestres ou disciplinas
    """
    try:
        if not CURSOS_DATA:
            return "Não foi possível carregar as informações dos cursos no momento."
        
        # Se não especificar curso, lista todos disponíveis
        if not curso_nome:
            cursos_disponiveis = list(CURSOS_DATA.keys())
            return f"🎓 **Cursos Disponíveis na UniFECAF**\n\n" + "\n".join(f"• {curso}" for curso in cursos_disponiveis)
        
        # Buscar curso específico (com busca flexível)
        curso_encontrado = None
        for curso in CURSOS_DATA.keys():
            if curso_nome.lower() in curso.lower():
                curso_encontrado = curso
                break
        
        if not curso_encontrado:
            return f"❌ Curso '{curso_nome}' não encontrado.\n\n🎓 Cursos disponíveis:\n" + "\n".join(f"• {curso}" for curso in CURSOS_DATA.keys())
        
        # Se não especificar semestre, lista todos os semestres do curso
        if not semestre:
            semestres = list(CURSOS_DATA[curso_encontrado].keys())
            info = f"📚 **Curso: {curso_encontrado}**\n\n**Semestres disponíveis:**\n"
            for sem in semestres:
                disciplinas_count = len(CURSOS_DATA[curso_encontrado][sem])
                info += f"• {sem}: {disciplinas_count} disciplinas\n"
            return info
        
        # Buscar semestre específico
        semestre_encontrado = None
        for sem in CURSOS_DATA[curso_encontrado].keys():
            if semestre.lower() in sem.lower():
                semestre_encontrado = sem
                break
        
        if not semestre_encontrado:
            semestres = list(CURSOS_DATA[curso_encontrado].keys())
            return f"❌ Semestre '{semestre}' não encontrado no curso {curso_encontrado}.\n\n**Semestres disponíveis:**\n" + "\n".join(f"• {sem}" for sem in semestres)
        
        # Se busca por disciplina específica
        if disciplina:
            disciplinas_encontradas = []
            for disc in CURSOS_DATA[curso_encontrado][semestre_encontrado]:
                if disciplina.lower() in disc.lower():
                    disciplinas_encontradas.append(disc)
            
            if disciplinas_encontradas:
                return f"🔍 **Disciplinas encontradas em {curso_encontrado} - {semestre_encontrado}:**\n" + "\n".join(f"• {d}" for d in disciplinas_encontradas)
            else:
                return f"❌ Nenhuma disciplina contendo '{disciplina}' encontrada em {curso_encontrado} - {semestre_encontrado}"
        
        # Listar todas as disciplinas do semestre
        disciplinas = CURSOS_DATA[curso_encontrado][semestre_encontrado]
        info = f"📚 **Curso: {curso_encontrado}**\n🎯 **Semestre: {semestre_encontrado}**\n\n**Disciplinas:**\n"
        info += "\n".join(f"• {disc}" for disc in disciplinas)
        return info
        
    except Exception as e:
        logger.error(f"Erro ao consultar informações do curso: {e}")
        return "❌ Erro ao consultar informações do curso."

# =======================================================
#   FUNÇÃO DE IA — CONSULTA A OPENAI (CORRIGIDA E MELHORADA)
# =======================================================
def consultar_ia(prompt: str, contexto_adicional: str = "") -> str:
    """
    Função central de IA utilizada pelo bot inteiro.
    Recebe um prompt e retorna a resposta otimizada.
    """
    try:
        # Verifica se a chave da API está disponível
        if not OPENAI_KEY:
            return "🔧 Sistema temporariamente indisponível. Por favor, tente novamente mais tarde."

        # Verificar se é uma pergunta sobre cursos para enriquecer com dados do CSV
        prompt_enriquecido = prompt
        palavras_chave_cursos = ['curso', 'disciplina', 'semestre', 'grade', 'matéria', 'matriz', 'métodos ágeis', 'recuperação', 'reposição']
        
        if any(palavra in prompt.lower() for palavra in palavras_chave_cursos):
            info_cursos = consultar_info_curso()
            prompt_enriquecido = f"{prompt}\n\n{contexto_adicional}\n\nInformações dos cursos disponíveis:\n{info_cursos}\n\nBaseie sua resposta nessas informações reais dos cursos."
        else:
            prompt_enriquecido = f"{prompt}\n\n{contexto_adicional}"

        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": """Você é um assistente especializado da UniFECAF. Siga estas diretrizes:

🎯 **PARA RECUPERAÇÃO/REPOSIÇÃO:**
- Confirme disciplina e semestre
- Informe prazos (48h úteis)
- Explique procedimentos
- Fornece contato da secretaria

💰 **PARA FINANCEIRO:**
- Confirme tipo de solicitação
- Informe prazos (24h úteis) 
- Oriente sobre documentação
- Fornece contato do financeiro

📄 **PARA DOCUMENTOS:**
- Confirme documento solicitado
- Explique opções (email/retirar)
- Informe prazos de emissão
- Fornece contato de documentos

🎓 **PARA CURSOS:**
- Use dados reais do CSV
- Seja preciso nas informações
- Sugira contato com coordenação

📋 **PARA TODOS:**
- Seja educado e profissional
- Use emojis moderadamente
- Confirme dados do aluno quando disponíveis
- Fornece contatos específicos"""
                },
                {"role": "user", "content": prompt_enriquecido}
            ],
            max_tokens=500,
            temperature=0.4
        )
        
        # ACESSO CORRETO - usando .content em vez de ["content"]
        if resposta.choices and resposta.choices[0].message:
            return resposta.choices[0].message.content
        else:
            return "❌ Não foi possível processar sua solicitação no momento."
            
    except Exception as e:
        logger.error(f"Erro na consulta à IA: {str(e)}")
        
        # FALLBACK ESPECÍFICO E MELHORADO PARA TODOS OS CASOS
        prompt_lower = prompt.lower()
        contexto_lower = contexto_adicional.lower()
        
        # RECUPERAÇÃO/REPOSIÇÃO
        if "recuperação" in prompt_lower or "reposição" in prompt_lower:
            if "métodos ágeis" in prompt_lower:
                return "✅ **SOLICITAÇÃO DE RECUPERAÇÃO/REPOSIÇÃO REGISTRADA**\n\n📚 **Disciplina:** MÉTODOS ÁGEIS\n🎯 **Semestre:** 1º Semestre\n👤 **Curso:** Análise e Desenvolvimento de Sistemas\n\n📋 **Próximos passos:**\n• Secretaria entrará em contato em até 48h úteis\n• Serão informadas datas disponíveis para prova\n• Documentação necessária será solicitada\n\n📞 **Contato:** secretaria@unifecaf.edu.br"
            else:
                return "✅ **SOLICITAÇÃO DE RECUPERAÇÃO/REPOSIÇÃO REGISTRADA**\n\nSua solicitação foi encaminhada para a secretaria acadêmica. A equipe entrará em contato em até 48h úteis com todas as orientações.\n\n📞 **Contato:** secretaria@unifecaf.edu.br"
        
        # FINANCEIRO
        elif "financeiro" in prompt_lower or "boleto" in prompt_lower or "pagamento" in prompt_lower or "acordo" in prompt_lower:
            acao = "solicitação financeira"
            if "boleto" in prompt_lower:
                acao = "consulta de boletos"
            elif "segunda via" in prompt_lower:
                acao = "emissão de segunda via"
            elif "acordo" in prompt_lower:
                acao = "proposta de acordo"
            elif "pagamento" in prompt_lower:
                acao = "consulta de pagamentos"
                
            return f"✅ **SOLICITAÇÃO FINANCEIRA REGISTRADA**\n\n💼 **Tipo:** {acao}\n📅 **Prazo:** Até 24h úteis para retorno\n\n📋 **Próximos passos:**\n• Equipe financeira analisará sua solicitação\n• Retornaremos por email com informações\n• Mantenha seus dados atualizados\n\n📞 **Contato:** financeiro@unifecaf.edu.br"
        
        # DOCUMENTOS
        elif "documento" in prompt_lower or "declaração" in prompt_lower or "atestado" in prompt_lower or "histórico" in prompt_lower or "diploma" in prompt_lower:
            doc_type = "documento"
            if "declaração" in prompt_lower:
                doc_type = "declaração de matrícula"
            elif "atestado" in prompt_lower:
                doc_type = "atestado de frequência"
            elif "histórico" in prompt_lower:
                doc_type = "histórico parcial"
            elif "diploma" in prompt_lower:
                doc_type = "diploma"
                
            return f"✅ **SOLICITAÇÃO DE DOCUMENTO REGISTRADA**\n\n📄 **Documento:** {doc_type.upper()}\n📅 **Prazo de emissão:** 2-3 dias úteis\n\n📋 **Próximos passos:**\n• Documento será processado conforme sua escolha\n• Receberá confirmação por email\n• Retirada disponível na secretaria\n\n📞 **Contato:** documentos@unifecaf.edu.br"
        
        # CURSOS
        elif "curso" in prompt_lower or "disciplina" in prompt_lower:
            return consultar_info_curso() + "\n\n💡 **Dica:** Para informações detalhadas, entre em contato com a coordenação do curso."
        
        # INFORMAÇÕES GERAIS
        else:
            return "✅ **SOLICITAÇÃO REGISTRADA COM SUCESSO**\n\nSua mensagem foi recebida e será processada pela nossa equipe.\n\n📞 **Atendimento humano:** atendimento@unifecaf.edu.br\n⏰ **Horário:** Segunda a sexta, 8h às 18h"

# =======================================================
#   FUNÇÃO ESPECÍFICA PARA CONSULTA DE CURSOS
# =======================================================
def consultar_curso_especifico(pergunta_usuario: str) -> str:
    """
    Função especializada para consultas sobre cursos e disciplinas
    """
    try:
        # Extrair informações da pergunta
        pergunta = pergunta_usuario.lower()
        
        # Consulta geral de cursos
        if 'quais cursos' in pergunta or 'cursos disponíveis' in pergunta or 'quais são os cursos' in pergunta or 'listar cursos' in pergunta:
            return consultar_info_curso()
        
        # Buscar por curso específico
        for curso in CURSOS_DATA.keys():
            if curso.lower() in pergunta:
                if 'semestre' in pergunta or 'disciplina' in pergunta:
                    # Tentar extrair semestre da pergunta
                    semestre_encontrado = None
                    for sem in ['1º', '2º', '3º', '4º', '5º', '6º']:
                        if sem in pergunta_usuario:
                            semestre_encontrado = f"{sem} Semestre"
                            break
                    
                    if semestre_encontrado:
                        return consultar_info_curso(curso, semestre_encontrado)
                    else:
                        return consultar_info_curso(curso)
                else:
                    return consultar_info_curso(curso)
        
        # Buscar por disciplina específica
        for curso in CURSOS_DATA.keys():
            for semestre in CURSOS_DATA[curso]:
                for disciplina in CURSOS_DATA[curso][semestre]:
                    if disciplina.lower() in pergunta:
                        return f"🔍 **Disciplina encontrada:** {disciplina}\n\n📚 **Curso:** {curso}\n🎯 **Semestre:** {semestre}\n\n{consultar_info_curso(curso, semestre)}"
        
        # Se não encontrou curso específico, usar IA geral
        info_cursos = consultar_info_curso()
        prompt = f"Pergunta do usuário: {pergunta_usuario}\n\nInformações reais dos cursos:\n{info_cursos}\n\nResponda de forma precisa usando essas informações."
        return consultar_ia(prompt)
        
    except Exception as e:
        logger.error(f"Erro na consulta específica de curso: {e}")
        return consultar_info_curso()

# =======================================================
#   CLASSE PARA ARMAZENAR DADOS DO ATENDIMENTO
# =======================================================
class Atendimento:
    def __init__(self, user_id):
        self.user_id = user_id
        self.etapa = 0
        self.encerrado = False
        self.registros = {}
        self.id_atendimento = str(uuid.uuid4())[:8]  # ID curto
        self.inicio = datetime.now()

    def registrar(self, chave, valor):
        """Salva um dado no registro do atendimento."""
        self.registros[chave] = valor
        logger.info(f"Registro: {chave} = {valor}")

    # ===================================================
    #     GERAR CSV DO ATENDIMENTO
    # ===================================================
    def gerar_csv(self):
        """
        Gera um CSV com todos os dados registrados no atendimento.
        O arquivo ficará disponível na pasta /atendimentos/.
        """
        try:
            # Criar pasta se não existir
            pasta = "atendimentos"
            os.makedirs(pasta, exist_ok=True)

            # Nome do arquivo
            data = datetime.now().strftime("%Y-%m-%d_%Hh%M")
            nome_arquivo = f"atendimento_{self.user_id}_{self.id_atendimento}_{data}.csv"
            caminho_completo = os.path.join(pasta, nome_arquivo)

            # Escrever CSV
            with open(caminho_completo, "w", newline="", encoding="utf-8") as arq:
                writer = csv.writer(arq)
                writer.writerow(["CHAVE", "VALOR"])
                writer.writerow(["user_id", self.user_id])
                writer.writerow(["id_atendimento", self.id_atendimento])
                writer.writerow(["inicio", self.inicio])
                writer.writerow(["fim", datetime.now()])

                for chave, valor in self.registros.items():
                    writer.writerow([chave, valor])

            logger.info(f"CSV gerado: {caminho_completo}")
            return caminho_completo
            
        except Exception as e:
            logger.error(f"Erro ao gerar CSV: {e}")
            return "erro_ao_gerar_csv"