import customtkinter as ctk
import csv
from datetime import datetime
import os
import sqlite3

# Classe para gerenciar o banco de dados
class DatabaseManager:
    def __init__(self, db_name='monitoramento_energia.db'):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._criar_tabelas()
    
    def _criar_tabelas(self):
        """Cria as tabelas necessárias no banco de dados"""
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS dispositivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            potencia_watts REAL NOT NULL
        )
        ''')
        
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS registros_consumo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE NOT NULL,
            hora TIME NOT NULL,
            dispositivo_id INTEGER NOT NULL,
            tempo_ligado REAL NOT NULL,
            consumo_kwh REAL NOT NULL,
            FOREIGN KEY (dispositivo_id) REFERENCES dispositivos(id)
        )
        ''')
        self.conn.commit()
    
    def adicionar_dispositivo(self, nome, potencia_watts):
        """Adiciona um novo dispositivo à tabela"""
        try:
            self.cursor.execute(
                "INSERT INTO dispositivos (nome, potencia_watts) VALUES (?, ?)",
                (nome, potencia_watts)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def remover_dispositivo(self, nome):
        """Remove um dispositivo da tabela"""
        self.cursor.execute("DELETE FROM dispositivos WHERE nome = ?", (nome,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def obter_dispositivos(self):
        """Retorna todos os dispositivos cadastrados"""
        self.cursor.execute("SELECT id, nome, potencia_watts FROM dispositivos")
        return self.cursor.fetchall()
    
    def registrar_consumo(self, dispositivo_id, tempo_ligado, consumo_kwh):
        """Registra o consumo de um dispositivo"""
        data_atual = datetime.now().strftime("%Y-%m-%d")
        hora_atual = datetime.now().strftime("%H:%M:%S")
        
        self.cursor.execute('''
        INSERT INTO registros_consumo 
        (data, hora, dispositivo_id, tempo_ligado, consumo_kwh)
        VALUES (?, ?, ?, ?, ?)
        ''', (data_atual, hora_atual, dispositivo_id, tempo_ligado, consumo_kwh))
        self.conn.commit()
    
    def obter_relatorio_diario(self, data=None):
        """Obtém um relatório de consumo para uma data específica"""
        if data is None:
            data = datetime.now().strftime("%Y-%m-%d")
        
        self.cursor.execute('''
        SELECT d.nome, r.tempo_ligado, r.consumo_kwh 
        FROM registros_consumo r
        JOIN dispositivos d ON r.dispositivo_id = d.id
        WHERE r.data = ?
        ''', (data,))
        return self.cursor.fetchall()
    
    def fechar_conexao(self):
        """Fecha a conexão com o banco de dados"""
        self.conn.close()

# Classe para representar cada dispositivo elétrico
class DispositivoEletrico:
    def __init__(self, nome, potencia_watts):
        self.nome = nome
        self.potencia_watts = potencia_watts
        self.tempo_ligado = 0

    def consumo_atual(self):
        consumo = (self.potencia_watts * self.tempo_ligado) / 1000
        return consumo

# Sistema de monitoramento de energia
class SistemaMonitoramentoEnergia:
    def __init__(self, tarifa_kwh):
        self.dispositivos = []
        self.tarifa_kwh = tarifa_kwh
        self.db = DatabaseManager()
        self._carregar_dispositivos_db()
    
    def _carregar_dispositivos_db(self):
        """Carrega os dispositivos do banco de dados"""
        dispositivos_db = self.db.obter_dispositivos()
        for id, nome, potencia in dispositivos_db:
            self.dispositivos.append(DispositivoEletrico(nome, potencia))
    
    def adicionar_dispositivo(self, dispositivo):
        if self.db.adicionar_dispositivo(dispositivo.nome, dispositivo.potencia_watts):
            self.dispositivos.append(dispositivo)
            return True
        return False
    
    def remover_dispositivo(self, nome_dispositivo):
        if self.db.remover_dispositivo(nome_dispositivo):
            self.dispositivos = [d for d in self.dispositivos if d.nome != nome_dispositivo]
            return True
        return False
    
    def consumo_total(self):
        return sum([d.consumo_atual() for d in self.dispositivos])
    
    def calcular_custo(self):
        return self.consumo_total() * self.tarifa_kwh
    
    def registrar_consumos(self):
        """Registra o consumo de todos os dispositivos no banco de dados"""
        dispositivos_db = self.db.obter_dispositivos()
        dispositivo_para_id = {nome: id for id, nome, _ in dispositivos_db}
        
        for dispositivo in self.dispositivos:
            dispositivo_id = dispositivo_para_id.get(dispositivo.nome)
            if dispositivo_id is not None:
                self.db.registrar_consumo(
                    dispositivo_id,
                    dispositivo.tempo_ligado,
                    dispositivo.consumo_atual()
                )

def mostrar_relatorio(sistema):
    janela = ctk.CTk()
    janela.title("Relatório Diário")
    janela.geometry("750x550")  # Tamanho um pouco maior para os novos botões
    janela.configure(fg_color="black")
    
    # Frame principal com rolagem
    main_frame = ctk.CTkFrame(janela, fg_color="black")
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Canvas e Scrollbar
    canvas = ctk.CTkCanvas(main_frame, bg="black", highlightthickness=0)
    scrollbar = ctk.CTkScrollbar(main_frame, orientation="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Frame interno
    container = ctk.CTkFrame(canvas, fg_color="black")
    canvas.create_window((0, 0), window=container, anchor="nw")
    
    def deletar_registro(data, dispositivo_id):
        """Remove um registro específico do banco de dados"""
        sistema.db.cursor.execute('''
        DELETE FROM registros_consumo 
        WHERE date(data) = ? AND dispositivo_id = ?
        ''', (data, dispositivo_id))
        sistema.db.conn.commit()
        atualizar_relatorio()  # Atualiza a visualização após deletar
    
    def carregar_dados():
        """Consulta SQL para pegar todos os registros com IDs necessários"""
        sistema.db.cursor.execute('''
        SELECT 
            date(r.data) as data_formatada,
            d.id as dispositivo_id,
            d.nome,
            SUM(r.tempo_ligado) as tempo_total,
            SUM(r.consumo_kwh) as consumo_total
        FROM registros_consumo r
        JOIN dispositivos d ON r.dispositivo_id = d.id
        GROUP BY date(r.data), d.id
        ORDER BY date(r.data) DESC
        ''')
        return sistema.db.cursor.fetchall()
    
    def atualizar_relatorio():
        """Atualiza todo o conteúdo do relatório"""
        # Limpar container
        for widget in container.winfo_children():
            widget.destroy()
        
        dados = carregar_dados()
        
        if not dados:
            ctk.CTkLabel(
                container,
                text="Nenhum dado de consumo encontrado",
                text_color="white"
            ).pack(pady=20)
            return
        
        # Agrupar por data
        dias = {}
        consumo_total_geral = 0
        custo_total_geral = 0
        
        for data, dispositivo_id, nome, tempo, consumo in dados:
            if data not in dias:
                dias[data] = []
            dias[data].append((dispositivo_id, nome, tempo, consumo))
            consumo_total_geral += consumo
            custo_total_geral += consumo * sistema.tarifa_kwh
        
        # Criar widgets para cada dia
        for data in sorted(dias.keys(), reverse=True):
            frame = ctk.CTkFrame(container, fg_color="#1a1a1a", corner_radius=8)
            frame.pack(fill="x", pady=5, padx=5)
            
            # Cabeçalho do dia
            header = ctk.CTkButton(
                frame,
                text=f"{data} ▼",
                command=lambda f=frame: toggle_detalhes(f),
                corner_radius=8,
                fg_color="#1a1a1a",
                hover_color="#333333",
                anchor="w",
                text_color="white"
            )
            header.pack(fill="x", pady=2)
            
            # Área de conteúdo (inicialmente oculta)
            content = ctk.CTkFrame(frame, fg_color="#1a1a1a")
            
            # Adicionar dispositivos com botão de deletar
            for dispositivo_id, nome, tempo, consumo in dias[data]:
                row = ctk.CTkFrame(content, fg_color="#1a1a1a")
                row.pack(fill="x", pady=2, padx=10)
                
                # Informações do dispositivo
                info_frame = ctk.CTkFrame(row, fg_color="#1a1a1a")
                info_frame.pack(side="left", fill="x", expand=True)
                
                ctk.CTkLabel(
                    info_frame,
                    text=f"{nome}: {tempo:.2f}h = {consumo:.3f}kWh (R$ {consumo * sistema.tarifa_kwh:.2f})",
                    text_color="white"
                ).pack(side="left")
                
                # Botão para deletar
                btn_deletar = ctk.CTkButton(
                    row,
                    text="×",
                    width=30,
                    height=30,
                    fg_color="#ff4444",
                    hover_color="#ff6666",
                    command=lambda d=data, did=dispositivo_id: deletar_registro(d, did)
                )
                btn_deletar.pack(side="right", padx=5)
        
        # Rodapé com totais
        footer = ctk.CTkFrame(container, fg_color="#333333", corner_radius=8)
        footer.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(
            footer,
            text=f"CONSUMO TOTAL: {consumo_total_geral:.3f}kWh",
            text_color="white",
            font=("Arial", 12, "bold")
        ).pack(side="left", padx=10, pady=5)
        
        ctk.CTkLabel(
            footer,
            text=f"CUSTO TOTAL: R$ {custo_total_geral:.2f}",
            text_color="#4CAF50",
            font=("Arial", 12, "bold")
        ).pack(side="right", padx=10, pady=5)
        
        canvas.configure(scrollregion=canvas.bbox("all"))
    
    def toggle_detalhes(frame):
        """Alterna entre mostrar/esconder detalhes de um dia"""
        for child in frame.winfo_children():
            if isinstance(child, ctk.CTkFrame) and child != frame.winfo_children()[0]:
                if child.winfo_ismapped():
                    child.pack_forget()
                    frame.winfo_children()[0].configure(
                        text=frame.winfo_children()[0].cget("text").replace("▼", "▶")
                    )
                else:
                    child.pack(fill="x", pady=5)
                    frame.winfo_children()[0].configure(
                        text=frame.winfo_children()[0].cget("text").replace("▶", "▼")
                    )
        canvas.configure(scrollregion=canvas.bbox("all"))
    
    # Configurar rolagem com mouse
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    canvas.bind_all("<MouseWheel>", on_mousewheel)
    
    # Botão de atualização
    btn_frame = ctk.CTkFrame(janela, fg_color="black")
    btn_frame.pack(pady=5)
    
    ctk.CTkButton(
        btn_frame,
        text="↻ Atualizar Relatório",
        command=atualizar_relatorio,
        fg_color="#333333",
        hover_color="#555555"
    ).pack()
    
    # Carregar dados inicialmente
    atualizar_relatorio()
    
    janela.mainloop()

def iniciar_sistema():
    tarifa_kwh = 0.18895
    sistema = SistemaMonitoramentoEnergia(tarifa_kwh)
    
    # Adiciona dispositivos padrão se o banco estiver vazio
    if not sistema.db.obter_dispositivos():
        dispositivos_padrao = [
            ("Geladeira", 250.0),
            ("Lâmpada da Sala", 60.0),
            ("Lâmpada da Cozinha", 60.0),
            ("Lâmpada do Banheiro", 60.0),
            ("Chuveiro do Banheiro", 2100.0),
            ("Ar-condicionado", 2000.0),
            ("Tv", 100.0)
        ]
        
        for nome, potencia in dispositivos_padrao:
            sistema.db.adicionar_dispositivo(nome, potencia)
        
        sistema._carregar_dispositivos_db()
    
    return sistema

def interface_principal(sistema):
    janela = ctk.CTk()
    janela.title("Sistema de Monitoramento de Energia")
    janela.geometry("350x550")
    
    ctk.CTkLabel(janela, text="Sistema de Monitoramento de Energia", font=("Arial", 16)).pack(pady=10)
    ctk.CTkButton(janela, text="Monitorar Dispositivos", command=lambda: monitorar_dispositivos(sistema)).pack(pady=5)
    ctk.CTkButton(janela, text="Adicionar Dispositivo", command=lambda: adicionar_dispositivo(sistema)).pack(pady=5)
    ctk.CTkButton(janela, text="Remover Dispositivo", command=lambda: remover_dispositivo(sistema)).pack(pady=5)
    ctk.CTkButton(janela, text="Ver Relatório", command=lambda: mostrar_relatorio(sistema)).pack(pady=5)
    ctk.CTkButton(janela, text="Sair", command=janela.destroy).pack(pady=5)
    
    janela.mainloop()

def adicionar_dispositivo(sistema):
    janela = ctk.CTk()
    janela.title("Adicionar Dispositivo")
    janela.geometry("350x300")
    
    def adicionar_novo_dispositivo():
        nome = nome_entry.get()
        try:
            potencia = float(potencia_entry.get())
            novo_dispositivo = DispositivoEletrico(nome, potencia)
            if sistema.adicionar_dispositivo(novo_dispositivo):
                resultado_label.configure(text=f"Dispositivo '{nome}' adicionado com sucesso!", text_color="green")
            else:
                resultado_label.configure(text=f"Dispositivo '{nome}' já existe!", text_color="red")
        except ValueError:
            resultado_label.configure(text="Erro: Insira um valor numérico válido.", text_color="red")
    
    ctk.CTkLabel(janela, text="Adicionar Novo Dispositivo").pack(pady=10)
    ctk.CTkLabel(janela, text="Nome do dispositivo:").pack()
    nome_entry = ctk.CTkEntry(janela)
    nome_entry.pack(pady=5)
    
    ctk.CTkLabel(janela, text="Potência (em Watts):").pack()
    potencia_entry = ctk.CTkEntry(janela)
    potencia_entry.pack(pady=5)
    
    ctk.CTkButton(janela, text="Adicionar", command=adicionar_novo_dispositivo).pack(pady=10)
    ctk.CTkButton(janela, text="Voltar", command=janela.destroy).pack(pady=5)
    
    resultado_label = ctk.CTkLabel(janela, text="")
    resultado_label.pack(pady=10)
    
    janela.mainloop()

def remover_dispositivo(sistema):
    janela = ctk.CTk()
    janela.title("Remover Dispositivo")
    janela.geometry("350x300")
    
    def remover_selecionado():
        dispositivo_selecionado = listbox.get()
        if dispositivo_selecionado:
            if sistema.remover_dispositivo(dispositivo_selecionado):
                resultado_label.configure(text=f"Dispositivo '{dispositivo_selecionado}' removido com sucesso!", text_color="green")
                listbox.configure(values=[d.nome for d in sistema.dispositivos])
            else:
                resultado_label.configure(text=f"Erro ao remover dispositivo '{dispositivo_selecionado}'", text_color="red")
        else:
            resultado_label.configure(text="Selecione um dispositivo para remover.", text_color="red")
    
    ctk.CTkLabel(janela, text="Remover Dispositivo").pack(pady=10)
    ctk.CTkLabel(janela, text="Selecione o dispositivo:").pack()
    
    listbox = ctk.CTkComboBox(janela, values=[d.nome for d in sistema.dispositivos])
    listbox.pack(pady=10)
    
    ctk.CTkButton(janela, text="Remover", command=remover_selecionado).pack(pady=5)
    ctk.CTkButton(janela, text="Voltar", command=janela.destroy).pack(pady=5)
    
    resultado_label = ctk.CTkLabel(janela, text="")
    resultado_label.pack(pady=10)
    
    janela.mainloop()

def monitorar_dispositivos(sistema):
    janela = ctk.CTk()
    janela.title("Monitorar Dispositivos")
    janela.geometry("600x600")
    
    dispositivos_inputs = {}
    
    def calcular_consumo():
        try:
            for dispositivo in sistema.dispositivos:
                tempo_str = dispositivos_inputs[dispositivo.nome].get()
                dispositivo.tempo_ligado = float(tempo_str)
            
            consumo_total = sistema.consumo_total()
            custo_total = sistema.calcular_custo()
            
            resultado_label.configure(
                text=f"Consumo total: {consumo_total:.4f} kWh\nCusto total: R$ {custo_total:.2f}",
                text_color="white"
            )
        except ValueError:
            resultado_label.configure(text="Erro: Insira valores válidos.", text_color="red")
    
    def salvar_dados():
        try:
            sistema.registrar_consumos()
            salvar_monitoramento_em_csv(sistema)
            resultado_label.configure(text="Dados salvos com sucesso!", text_color="green")
        except Exception as e:
            resultado_label.configure(text=f"Erro ao salvar os dados: {e}", text_color="red")
    
    ctk.CTkLabel(janela, text="Monitoramento de Energia Residencial", font=("Arial", 16)).pack(pady=10)
    ctk.CTkLabel(janela, text="Insira o tempo ligado em horas (ex: 1.5 para 1h30min)", font=("Arial", 12)).pack(pady=5)
    
    for dispositivo in sistema.dispositivos:
        frame = ctk.CTkFrame(janela)
        frame.pack(pady=5)
        ctk.CTkLabel(frame, text=f"{dispositivo.nome} ({dispositivo.potencia_watts} W):").pack(side="left")
        dispositivos_inputs[dispositivo.nome] = ctk.CTkEntry(frame, width=100)
        dispositivos_inputs[dispositivo.nome].pack(side="left", padx=10)
    
    resultado_label = ctk.CTkLabel(janela, text="", font=("Arial", 12))
    resultado_label.pack(pady=10)
    
    ctk.CTkButton(janela, text="Calcular Consumo", command=calcular_consumo).pack(pady=5)
    ctk.CTkButton(janela, text="Salvar Dados", command=salvar_dados).pack(pady=5)
    ctk.CTkButton(janela, text="Voltar", command=janela.destroy).pack(pady=5)
    janela.mainloop()

def salvar_monitoramento_em_csv(sistema):
    nome_arquivo = "monitoramento_energia.csv"
    campos = ['Data', 'Hora', 'Dispositivo', 'Tempo Ligado (h)', 'Consumo (kWh)']
    
    escrever_cabecalho = not os.path.isfile(nome_arquivo)
    
    with open(nome_arquivo, mode='a', newline='') as arquivo_csv:
        escritor_csv = csv.writer(arquivo_csv)
        if escrever_cabecalho:
            escritor_csv.writerow(campos)
        
        for dispositivo in sistema.dispositivos:
            data_atual = datetime.now().strftime("%Y-%m-%d")
            hora_atual = datetime.now().strftime("%H:%M:%S")
            linha = [
                data_atual,
                hora_atual,
                dispositivo.nome,
                dispositivo.tempo_ligado,
                dispositivo.consumo_atual()
            ]
            escritor_csv.writerow(linha)

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    
    sistema = iniciar_sistema()
    interface_principal(sistema)
    
    # Fechar a conexão com o banco de dados ao sair
    sistema.db.fechar_conexao()