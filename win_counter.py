import os 
import json
import discord
from discord import app_commands
import gspread
from datetime import datetime
from collections import Counter
import re  
from dotenv import load_dotenv

# Invoca o arquivo .env (Se ele não existir, o código só ignora e segue a vida)
load_dotenv()

# ==========================================
# 1. CONFIGURAÇÕES
# ==========================================
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
PLANILHA_ID = os.getenv('PLANILHA_ID')

# Dicionário de atalhos (Aliases). Você pode adicionar mais jogos aqui depois!
DICIONARIO_JOGOS = {
    "mtg": "Mtg: Commander",
    "magic": "Mtg: Commander",
    'penis': 'Penis'
}

# ==========================================
# 2. CONEXÃO COM GOOGLE SHEETS
# ==========================================
print("Conectando ao Google Sheets...")

google_creds_json = os.getenv('GOOGLE_CREDENTIALS')

if not google_creds_json:
    print("❌ ERRO CRÍTICO: Variável GOOGLE_CREDENTIALS não encontrada!")
    exit()
    
# 2. Converte a string JSON para um Dicionário Python
google_creds_dict = json.loads(google_creds_json)

# 3. Conecta passando o dicionário
gc = gspread.service_account_from_dict(google_creds_dict)

planilha = gc.open_by_key(PLANILHA_ID)
print("✅ Conectado ao Google Sheets!\n")

def traduzir_nome_jogo(jogo_digitado: str):
    """Verifica se o que o usuário digitou tem um atalho oficial. Se não tiver, capitaliza a string."""
    jogo_lower = jogo_digitado.strip().lower()
    return DICIONARIO_JOGOS.get(jogo_lower, jogo_digitado.strip().title())

def obter_ou_criar_aba(nome_jogo: str):
    """Verifica se o que o usuário digitou tem um atalho oficial. Se não tiver, capitaliza a string."""
    nome_oficial = traduzir_nome_jogo(nome_jogo)
    
    try:
        aba = planilha.worksheet(nome_oficial)
    except gspread.exceptions.WorksheetNotFound:
        print(f"Aba '{nome_oficial}' não encontrada. Criando...")
        aba = planilha.add_worksheet(title=nome_oficial, rows="1000", cols="4")
        aba.append_row(["Data", "UserID", "UserName", "Obs"], value_input_option="USER_ENTERED")
    
    return aba, nome_oficial

# ==========================================
# 3. SETUP DO BOT DISCORD
# ==========================================
class VitoriaBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True # Necessário para converter ID em Nome de Membro
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"Bot online e logado como {self.user}")

bot = VitoriaBot()

# ==========================================
# 4. COMANDOS SLASH
# ==========================================

@bot.tree.command(name="win", description="Registra uma vitória")
@app_commands.describe(texto="Ex: mtg @Geros combo infinito")
async def win(interaction: discord.Interaction, texto: str):
    await interaction.response.defer()

    try:
        # 1. Identificar se há menção de usuário no texto usando Regex
        match_mencao = re.search(r'<@!?(\d+)>', texto)
        
        if match_mencao:
            target_id = match_mencao.group(1)
            # Tenta pegar o membro no servidor para ter o nome atualizado
            membro = interaction.guild.get_member(int(target_id))
            user_id = str(target_id)
            user_name = membro.display_name if membro else "Desconhecido"
            user_mention = f"<@{target_id}>"
            # Limpa a menção do texto para não salvar o código <@ID> na planilha
            texto_limpo = re.sub(r'<@!?\d+>', '', texto).strip()
        else:
            user_id = str(interaction.user.id)
            user_name = interaction.user.display_name
            user_mention = interaction.user.mention
            texto_limpo = texto.strip()

        # 2. Lógica de separação Jogo vs Complementos
        partes = texto_limpo.split(" ", 1)
        if partes[0].lower() in DICIONARIO_JOGOS:
            jogo = partes[0]
            complementos = partes[1] if len(partes) > 1 else ""
        else:
            jogo = "mtg"
            complementos = texto_limpo

        data_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        aba, nome_oficial = obter_ou_criar_aba(jogo)
        
        aba.append_row([data_atual, user_id, user_name, complementos], value_input_option="USER_ENTERED")
        
        mensagem = f"🏆 Vitória de {user_mention} registrada no **{nome_oficial}**!"
        if complementos:
            mensagem += f" (**{complementos}**)"
            
        await interaction.followup.send(mensagem)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Erro ao salvar: {e}")

@bot.tree.command(name="mywins", description="Mostra o histórico de vitórias de um usuário")
@app_commands.describe(usuario="Selecione um usuário ou deixe em branco para ver as suas")
async def mywins(interaction: discord.Interaction, usuario: discord.Member = None):
    await interaction.response.defer()
    
    target = usuario or interaction.user
    target_id = str(target.id)
    
    try:
        abas = planilha.worksheets()
        historico = []

        for aba in abas:
            dados = aba.get_all_records()
            # Filtra vitórias desse ID específico nesta aba
            vitorias_aba = [d for d in dados if str(d.get("UserID")) == target_id]
            
            for v in vitorias_aba:
                historico.append({
                    "jogo": aba.title,
                    "data": v.get("Data", ""),
                    "obs": v.get("Obs", "")
                })

        if not historico:
            await interaction.followup.send(f"Nenhuma vitória encontrada para {target.mention}.")
            return

        # Ordena por data (as mais recentes primeiro)
        historico.reverse() 
        
        embeds = []
        itens_por_pagina = 15 # Quantidade de vitórias por página
        
        # Fatiamento (Chunking) para criar as páginas
       # Fatiamento (Chunking) para criar as páginas
        for i in range(0, len(historico), itens_por_pagina):
            chunk = historico[i:i + itens_por_pagina]
            texto_hist = ""
            
            for v in chunk:
                data_curta = str(v['data']).split(" ")[0] if v['data'] else "??"
                
                # SANITIZAÇÃO: Troca crase por apóstrofo pra não quebrar o layout do Discord
                obs_limpa = str(v['obs']).replace('`', "'") if v['obs'] else ""
                jogo_limpo = str(v['jogo']).replace('`', "'") if v['jogo'] else "??"
                
                obs_texto = f" - ({obs_limpa})" if obs_limpa else ""
                
                texto_hist += f"`{data_curta}` | **{jogo_limpo}**{obs_texto}\n"

            # Cria o Embed para esta página específica
            embed = discord.Embed(
                description=f"# Histórico: {target.display_name}\n\n{texto_hist}",
                color=0x3498db
            )
            
            # Adiciona um rodapé informando a página e o total de vitórias
            total_paginas = (len(historico) - 1) // itens_por_pagina + 1
            pagina_atual = (i // itens_por_pagina) + 1
            embed.set_footer(text=f"Página {pagina_atual} de {total_paginas} | Total de vitórias: {len(historico)}")
            
            embeds.append(embed)

        # Se só tiver 1 página, manda direto sem botões
        if len(embeds) == 1:
            await interaction.followup.send(embed=embeds[0])
        else:
            # Se tiver mais de 1, recicla a classe de paginação do Leaderboard
            view = PaginacaoLeaderboard(embeds)
            await interaction.followup.send(embed=embeds[0], view=view)

    except Exception as e:
        await interaction.followup.send(f"❌ Erro ao buscar histórico: {e}")

# Coloque esta classe ANTES do comando /leaderboard
class PaginacaoLeaderboard(discord.ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=180) # Os botões param de funcionar após 3 minutos
        self.embeds = embeds
        self.pagina_atual = 0
        self.atualizar_botoes()

    def atualizar_botoes(self):
        # Desativa o botão de voltar se estiver na primeira página"
        self.botao_voltar.disabled = self.pagina_atual == 0
        # Desativa o botão de avançar se estiver na última página
        self.botao_avancar.disabled = self.pagina_atual == len(self.embeds) - 1

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def botao_voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.pagina_atual -= 1
        self.atualizar_botoes()
        await interaction.response.edit_message(embed=self.embeds[self.pagina_atual], view=self)

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.secondary)
    async def botao_avancar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.pagina_atual += 1
        self.atualizar_botoes()
        await interaction.response.edit_message(embed=self.embeds[self.pagina_atual], view=self)


# O comando atualizado (agora sem pedir o parâmetro "jogo")
@bot.tree.command(name="leaderboard", description="Mostra o ranking de vitórias de todos os jogos")
async def leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        # Pega todas as abas da planilha de uma vez
        abas = planilha.worksheets()
        
        if not abas:
            await interaction.followup.send("Nenhum jogo registrado na planilha ainda.")
            return

        embeds = []

        # Percorre cada aba (jogo) para montar uma página
        for aba in abas:
            nome_jogo = aba.title
            registros = aba.get_all_records()
            
            if not registros:
                continue # Pula jogos que não têm nenhuma vitória registrada

            contagem = Counter(str(row["UserID"]) for row in registros)
            
            texto_ranking = ""
            
            for i, (u_id, vitorias) in enumerate(contagem.most_common(10), 1):
                if i == 1:
                    posicao = "🥇"
                elif i == 2:
                    posicao = "🥈"
                elif i == 3:
                    posicao = "🥉"
                else:
                    posicao = f"#{i}"
                
                # O '### ' no começo da string diz pro Discord aumentar o tamanho da fonte dessa linha inteira
                texto_ranking += f"{posicao} - <@{u_id}>: {vitorias} vitórias\n\n"

            # Injeta o Título gigante (H1) no topo da string
            texto_final = f"# Leaderboard - {nome_jogo}\n\n{texto_ranking}"

            # Cria o card sem o 'title', usando só a description turbinada
            embed = discord.Embed(
                description=texto_final,
                color=0x2ecc71
            )
            embeds.append(embed)

        if not embeds:
            await interaction.followup.send("Nenhum dado válido encontrado nas planilhas.")
            return

        # Se só tiver 1 jogo, manda direto sem botões
        if len(embeds) == 1:
            await interaction.followup.send(embed=embeds[0])
        else:
            # Se tiver mais de 1, chama a View com os botões
            view = PaginacaoLeaderboard(embeds)
            await interaction.followup.send(embed=embeds[0], view=view)

    except Exception as e:
        await interaction.followup.send(f"Erro ao buscar ranking: {e}")

# ==========================================
# 5. LIGAR O BOT
# ==========================================
import keep_alive # Importa o arquivo que você criou

# Inicia o mini-servidor web em background
keep_alive.keep_alive()

# Liga o bot do Discord
bot.run(DISCORD_TOKEN)