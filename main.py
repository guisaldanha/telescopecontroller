from frame_config import frmConfig
from frame_goto import frmGoto
from thread_update_values import UpdateValues
import tkinter as tk
from tkinter import ttk
from tkinter import font
import logandprint as log
from tooltip import ToolTip
import win32com.client
from tkinter import messagebox
import configparser
import os
import sys
from alpaca.telescope import *      # Multiple Classes including Enumerations
from alpaca.exceptions import *
import re
params = sys.argv
if '--debug' in params:
    log.debugMode(True)
else:
    log.enable(False)

class Controller:
    """
    The Controller class represents the main controller for the OnStep application.
    It handles the creation of the main window, user interface elements, and communication with the OnStepController.

    Args:
        window_width (int): The width of the main window. Default is 350.
        window_height (int): The height of the main window. Default is 320.
        margin_right (int): The right margin of the main window. Default is 20.
        margin_bottom (int): The bottom margin of the main window. Default is 90.
        title (str): The title of the main window. Default is "OnStep Controller".
    """
    def __init__(self, window_width=350, window_height=320, margin_right=20, margin_bottom=90, title="Telescope Controller"):
        super().__init__()

        self.log = log

        self.version = '1.0.0'

        # Configurações iniciais - Arquivo config.ini que tem as configurações de ip, porta e cache
        self.cache = self.get_config('COMMUNICATION', 'cache') or 0.5

        # Depois de criada a janela, verifica se o telescópio está conectado
        self.device_id = None
        driver = self.get_config('COMMUNICATION', 'driver')
        if driver:
            try:
                self.device_id = driver
                self.Telescope = win32com.client.Dispatch(driver)
                self.Telescope.Connected = True
                self.unpark()
            except Exception as e:
                log.error(f"Erro ao conectar com o telescópio: {e}")
                messagebox.showerror("Erro", f"Erro ao conectar com o telescópio: {e}")
                self.del_config('COMMUNICATION', 'driver')
                self.Telescope = None
                self.open_ascom_chooser()
        else:
            self.open_ascom_chooser()

        # self.telescope_properties()

        self.window_width = window_width
        self.window_height = window_height
        self.margin_right = margin_right
        self.margin_bottom = margin_bottom

        # Criando a janela
        self.root = tk.Tk()

        self.title = title
        self.root.title(self.title)
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.root.configure(pady=2)
        # Localização da janela no canto inferior direito da tela
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        posicaoX = self.root.winfo_screenwidth() - self.window_width - self.margin_right
        posicaoY = self.root.winfo_screenheight() - self.window_height - self.margin_bottom
        self.root.geometry(f"+{posicaoX}+{posicaoY}")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        # Cria os estilos dos botões de ação e movimento
        btnAction = ttk.Style()
        btnAction.configure("Action.TButton", foreground="blue")
        btnMovimentStyle = ttk.Style()
        btnMovimentStyle.configure("Moviment.TButton", foreground="blue")
        btnMovimentStyle.map("Moviment.TButton", foreground=[('pressed', 'red'), ('active', 'blue')])
        # Cria o estilo para os entrys de posição para que fiquem sem borda
        entryStyle = ttk.Style()
        entryStyle.element_create("plain.field", "from", "clam")
        entryStyle.layout("Pos.TEntry", [("Entry.plain.field", {"children": [("Entry.background", {"children": [("Entry.padding", {"children": [("Entry.textarea", {"sticky": "nswe"})]})]})]})])
        entryStyle.configure("Pos.TEntry", borderwidth=0)  # Define a borda como invisível
        entryStyle.map("Pos.TEntry", bordercolor=[('readonly', 'transparent')])  # Define a cor da borda para a mesma cor do fundo


        # ======= Frame principal
        self.frmMain = tk.Frame(self.root)
        self.create_frmMain()
        self.frmMain.pack(fill='both', expand=True)


        # ======== frmConfig
        self.frmConfig = frmConfig(self)

        # ======== frmGoto
        self.gotoInProgress = False
        self.frmGoto = frmGoto(self)

        self.root.update_idletasks()
        icon = '_internal/icon.ico'
        self.root.iconbitmap(icon)

        self.manual_slew = False
        self.going_home = False

        self.thread_update_values = UpdateValues(self)
        self.thread_update_values.daemon = True # Define a thread como daemon para que ela termine quando o programa principal terminar
        self.thread_update_values.start()

    def create_frmMain(self):
        # Label com o título da janela
        lblTitulo = ttk.Label(self.frmMain, text=self.title, font=("Segoe UI", 10, "bold"))
        lblTitulo.grid(row=0, column=0, columnspan=2, pady=5)

        frmBtnMove = tk.LabelFrame(self.frmMain, text="Movimento Manual")

        btnNW = ttk.Button(frmBtnMove, text=u"\u2196", width=5, style="Moviment.TButton")
        btnN = ttk.Button(frmBtnMove, text="N", width=5, style="Moviment.TButton")
        btnNE = ttk.Button(frmBtnMove, text=u"\u2197", width=5, style="Moviment.TButton")
        btnE = ttk.Button(frmBtnMove, text="L", width=5, style="Moviment.TButton")
        btnSE = ttk.Button(frmBtnMove, text=u"\u2198", width=5, style="Moviment.TButton")
        btnS = ttk.Button(frmBtnMove, text="S", width=5, style="Moviment.TButton")
        btnSO = ttk.Button(frmBtnMove, text=u"\u2199", width=5, style="Moviment.TButton")
        btnO = ttk.Button(frmBtnMove, text="O", width=5, style="Moviment.TButton")

        btnNW.grid(row=0, column=0, padx=2, pady=2)
        btnN.grid(row=0, column=1, padx=2, pady=2)
        btnNE.grid(row=0, column=2, padx=2, pady=2)
        btnE.grid(row=1, column=2, padx=2, pady=2)
        btnSE.grid(row=2, column=2, padx=2, pady=2)
        btnS.grid(row=2, column=1, padx=2, pady=2)
        btnSO.grid(row=2, column=0, padx=2, pady=2)
        btnO.grid(row=1, column=0, padx=2, pady=2)

        # Bind dos eventos de pressionar e soltar para os botões de moviment
        btnNW.bind("<ButtonPress-1>", lambda event: self.start_movement("NW"))
        btnNW.bind("<ButtonRelease-1>", lambda event: self.stop_movement("NW"))
        btnN.bind("<ButtonPress-1>", lambda event: self.start_movement("N"))
        btnN.bind("<ButtonRelease-1>", lambda event: self.stop_movement("N"))
        btnNE.bind("<ButtonPress-1>", lambda event: self.start_movement("NE"))
        btnNE.bind("<ButtonRelease-1>", lambda event: self.stop_movement("NE"))
        btnE.bind("<ButtonPress-1>", lambda event: self.start_movement("E"))
        btnE.bind("<ButtonRelease-1>", lambda event: self.stop_movement("E"))
        btnSE.bind("<ButtonPress-1>", lambda event: self.start_movement("SE"))
        btnSE.bind("<ButtonRelease-1>", lambda event: self.stop_movement("SE"))
        btnS.bind("<ButtonPress-1>", lambda event: self.start_movement("S"))
        btnS.bind("<ButtonRelease-1>", lambda event: self.stop_movement("S"))
        btnSO.bind("<ButtonPress-1>", lambda event: self.start_movement("SW"))
        btnSO.bind("<ButtonRelease-1>", lambda event: self.stop_movement("SW"))
        btnO.bind("<ButtonPress-1>", lambda event: self.start_movement("W"))
        btnO.bind("<ButtonRelease-1>", lambda event: self.stop_movement("W"))

        # Botão de stop
        btnStop = tk.Canvas(frmBtnMove, width=70, height=40)
        btnStop.grid(row=1, column=1, padx=0, pady=0)
        self.drawBtnStop(btnStop, 0, 0, 70, 40)
        btnStop.bind("<Button-1>", lambda event: [self.stop(), self.root.focus_set()])

        frmBtnMove.grid(row=1, column=0, padx=15, pady=5)
        # ======= Fim dos botões de moviment

        # ======= Parâmetros
        frmParam = tk.Frame(self.frmMain)

        # Velocidade de movimento
        self.axis_rate = tk.StringVar()
        self.axis_rate.set(1)
        frmSpeed = tk.LabelFrame(frmParam, text="Vel de movimento")
        frmSpeed.grid(row=1, column=3, padx=5, pady=5)
        possible_rates = self.get_possible_rates()
        self.comboSpeed = ttk.Combobox(frmSpeed, textvariable=self.axis_rate, values=possible_rates, width=15, state="readonly")
        self.comboSpeed.grid(row=1, column=3, padx=5, pady=5)
        self.comboSpeed.bind("<<ComboboxSelected>>", lambda event: [self.set_axis_rate((self.comboSpeed.get())), self.root.focus_set()])
        ToolTip(self.comboSpeed, "Velocidade do movimento manual", width=15)

        # Tracking
        self.tracking_rate = tk.StringVar()
        self.tracking_rate.set('Off')
        frmTrack = tk.LabelFrame(frmParam, text="Rastreamento")
        frmTrack.grid(row=2, column=3, padx=5, pady=5)
        possibleTracking = ['Off', 'Sideral', 'Lunar', 'Solar', 'King rate']
        self.comboTracking = ttk.Combobox(frmTrack, textvariable=self.tracking_rate, values=possibleTracking, width=15, state="readonly")
        self.comboTracking.grid(row=2, column=3, padx=5, pady=5)
        self.comboTracking.bind("<<ComboboxSelected>>", lambda event: [self.set_tracking(self.comboTracking.get()), self.root.focus_set()])

        frmParam.grid(row=1, column=1, padx=2, pady=2)
        # ======= Fim dos parâmetros

        self.tracking_rateMonitor = False

        # ======= Posição e botões de ação

        frmBottom = tk.Frame(self.frmMain)
        frmBottom.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

        frmPos = tk.LabelFrame(frmBottom, text="Posição da Montagem", width=20)
        frmPos.grid(row=0, rowspan=4, column=0, padx=20, pady=5)

        # Cria os labels dos eixos
        tk.Label(frmPos, text="RA").grid(row=0, column=0, sticky="e")
        tk.Label(frmPos, text="DEC").grid(row=1, column=0, sticky="e")
        tk.Label(frmPos, text="AZ").grid(row=2, column=0, sticky="e")
        tk.Label(frmPos, text="ALT").grid(row=3, column=0, sticky="e")

        # Valores dos eixos
        self.ra = tk.StringVar()
        self.dec = tk.StringVar()
        self.az = tk.StringVar()
        self.alt = tk.StringVar()

        # Cria os campos de texto
        self.entry_ra = ttk.Entry(frmPos, textvariable=self.ra, state="readonly", style="Pos.TEntry").grid(row=0, column=1, padx=2, pady=2)
        self.entry_dec = ttk.Entry(frmPos, textvariable=self.dec, state="readonly", style="Pos.TEntry").grid(row=1, column=1, padx=2, pady=2)
        self.entry_az = ttk.Entry(frmPos, textvariable=self.az, state="readonly", style="Pos.TEntry").grid(row=2, column=1, padx=2, pady=2)
        self.entry_alt = ttk.Entry(frmPos, textvariable=self.alt, state="readonly", style="Pos.TEntry").grid(row=3, column=1, padx=2, pady=2)

        self.btnFindHome = ttk.Button(frmBottom, text=u"\u2302 Go to Home", command=self.find_home, width=15)
        self.btnFindHome.grid(row=0, column=1, padx=10, pady=2)

        btnConfig = ttk.Button(frmBottom, text=u"\u2699 Config", command=self.show_frmConfig, width=15)
        btnConfig.grid(row=1, column=1, padx=10, pady=2)

        btnConfig = ttk.Button(frmBottom, text=u"\u2606 Goto", command=self.show_frmGoto, width=15)
        btnConfig.grid(row=2, column=1, padx=10, pady=2)

        btnClose = ttk.Button(frmBottom, text=u"\u2715 Fechar", command=self.close, width=15)
        btnClose.grid(row=3, column=1, padx=10, pady=2)

        # Rodapé
        self.statusMoviment = tk.StringVar()
        lblStatusMoviment = tk.Label(frmBottom, textvariable=self.statusMoviment, font=("Arial", 8), anchor="w", width=30)
        lblStatusMoviment.grid(row=4, column=0, pady=5)

        lblInfo = tk.Label(frmBottom, text=u"\u2139", foreground="blue", font=("Arial", 10), cursor="hand2")
        lblInfo.grid(row=4, column=3, padx=0, pady=0)
        lblInfo.bind("<Button-1>", lambda event: messagebox.showinfo("Sobre", "Controlador para o OnStep\nVersão " + self.version + "\nDesenvolvido por: Guilherme Saldanha\nE-mail: guisaldanha@gmail.com\nSite: guisaldanha.com\nGitHub: github.com/guisaldanha\n\nLicença: MIT - https://opensource.org/licenses/MIT\n\nPermissão de uso: Os usuários têm permissão para usar o software para qualquer finalidade, comercial ou não comercial.\n\nPermissão de modificação: Os usuários podem modificar o software como desejarem.\n\nRequisito de manutenção do aviso de copyright e da licença: Os usuários devem incluir uma cópia da licença e do aviso de copyright no software derivado.\n\nIsenção de responsabilidade: A licença isenta o autor do software de qualquer responsabilidade por danos decorrentes do uso ou distribuição do software.\n\nPara mais informações, acesse: https://guisaldanha.com/open-source/onstep/"))


    def drawBtnStop(self, canvas, x, y, width, height):
        """Desenha um hexágono branco em cima do círculo para ser usado como ícone de stop

        Args:
            canvas (tk.Canvas): canvas onde o ícone será desenhado
            x (int): coordenada x do ícone
            y (int): coordenada y do ícone
            width (int): largura do ícone
            height (int): altura do ícone
        """
        canvas.create_polygon(x + width * 0.3, y + height * 0.1,
                              x + width * 0.7, y + height * 0.1,
                              x + width * 0.9, y + height * 0.5,
                              x + width * 0.7, y + height * 0.9,
                              x + width * 0.3, y + height * 0.9,
                              x + width * 0.1, y + height * 0.5,
                              fill='red', outline='red')
        canvas.create_text(width / 2, height / 2, text="PARE", fill="white", font=("Helvetica", 9, "bold"))


    def start_movement(self, direcao):
        # Função chamada quando um botão de movimento é pressionado
        try:
            self.unpark()
            rate = float(self.axis_rate.get())
            self.manual_slew = True
            log.debug(f"Iniciando movimento para {direcao}")
            invert_ns = self.get_config('AXIS', 'invert_ns') == 'True'
            invert_ew = self.get_config('AXIS', 'invert_ew') == 'True'
            if 'N' in direcao:
                self.Telescope.MoveAxis(1, -rate if invert_ns else rate)
            if 'S' in direcao:
                self.Telescope.MoveAxis(1, rate if invert_ns else -rate)
            if 'E' in direcao:
                self.Telescope.MoveAxis(0, rate if invert_ew else -rate)
            if 'W' in direcao:
                self.Telescope.MoveAxis(0, -rate if invert_ew else rate)
            self.root.focus_set()
        except Exception as e:
            error_message = str(e)
            match = re.search(r'SlewError: (.+)', error_message)
            if match:
                error_reason = match.group(1)
            else:
                error_reason = error_message
            log.error(f"Erro ao iniciar movimento: {error_reason}")
            messagebox.showerror("Erro", f"Erro ao iniciar movimento: {error_reason}")
            self.manual_slew = False
            self.root.focus_set()


    def stop_movement(self, direcao):
        # Função chamada quando um botão de moviment é solto
        log.debug(f"Parando movimento para {direcao}")
        if 'N' or 'S' in direcao:
            self.Telescope.MoveAxis(1, 0)
        if 'E' or 'W' in direcao:
            self.Telescope.MoveAxis(0, 0)
        self.root.focus_set()
        self.manual_slew = False

    def stop(self):
        log.debug("Parando movimento")
        self.Telescope.AbortSlew()
        self.root.focus_set()

    def set_axis_rate(self, rate):
        """Atualiza a taxa de movimento da montagem."""
        if rate == '0.5 x sideral':
            rate = 0.000739
        elif rate == '1 x sideral':
            rate = 0.001478
        elif rate == '2 x sideral':
            rate = 0.002956
        else:
            rate = float(rate)
        self.axis_rate.set(rate)
        self.root.focus_set()

    def get_possible_rates(self):
        """Retorna as Updatings possíveis para movimentação da montagem. Serão oferecidas 9 Updatings entre rate.Minimum e rate.Maximum."""
        rates = []
        rates.append('0.5 x sideral') # 0.000739
        rates.append('1 x sideral') # 0.001478
        rates.append('2 x sideral') # 0.002956
        try:
            rate = self.Telescope.AxisRates(0)[0]
            log.debug(f'Taxa mínima: {rate.Minimum}, Taxa máxima: {rate.Maximum}')
            for i in range(1, 10):
                tax = round((rate.Minimum + ((rate.Maximum - rate.Minimum) / 9) * i) - 0.01, 2)
                rates.append(str(tax))
        except Exception as e:
            log.error(f"Erro ao obter as taxas de movimento: {e}")
            rates.append(str(0.100000))
            rates.append(str(0.250000))
            rates.append(str(0.500000))
            rates.append(str(1.000000))
            rates.append(str(2.000000))
            rates.append(str(3.000000))
        self.axis_rate.set(float(rates[4]))
        return rates

    def set_tracking(self, tracking):
        """Atualiza a taxa de rastreamento da montagem."""
        log.debug(f"Alterando rastreamento para {tracking}")
        if tracking == 'Off':
            self.Telescope.Tracking = False
        elif tracking == 'Sideral':
            self.Telescope.TrackingRate = 0
            self.Telescope.Tracking = True
        elif tracking == 'Lunar':
            self.Telescope.TrackingRate = 1
            self.Telescope.Tracking = True
        elif tracking == 'Solar':
            self.Telescope.TrackingRate = 2
            self.Telescope.Tracking = True
        elif tracking == 'King rate':
            self.Telescope.TrackingRate = 3
            self.Telescope.Tracking = True
        self.tracking_rate.set(tracking)
        log.debug(f"Rastreamento alterado para {self.Telescope.TrackingRate}")
        self.root.focus_set()

    def unpark(self):
        if self.Telescope.AtPark:
            if self.Telescope.CanUnpark:
                self.Telescope.Unpark()
                log.debug('Desparkeado')
            else:
                log.debug('Não é possível desparkear')
        else:
            log.debug('Já desparkeado')

    def park(self):
        if self.Telescope.CanPark:
            try:
                self.Telescope.Park()
                log.debug('Parkeado')
            except Exception as e:
                messagebox.showwarning("Atenção", "Em algumas montagens, após o parkeamento, a montagem é desconectada do Windows. Reconexão do cabo USB pode ser necessária. Para evitar esse tipo de problema, evite fazer o parkeamento da montagem usando esse programa.")
        else:
            log.debug('Não é possível parkear')


    def find_home(self):
        try:
            self.unpark()
            self.going_home = True
            log.debug('Enviando comando de home')
            if self.Telescope.CanFindHome:
                self.Telescope.FindHome()
            log.debug('Terminou o comando de home')
        except Exception as e:
            error_message = 'Houve um problema ao enviar o comando de home: ' + str(e)
            log.error(error_message)
            messagebox.showerror("Erro", error_message)


    def close(self):
        try:
            log.debug('Inicializando fechamento')
            if self.Telescope.Slewing or self.Telescope.Tracking:
                ask = messagebox.askyesno("Atenção", "A montagem está em movimento/rastreando. Deseja sair mesmo assim?")
                if not ask:
                    log.debug('Fechamento cancelado')
                    return
            self.thread_update_values.join()
            self.thread_update_values.stop()
            self.Telescope.Connected = False
            self.root.destroy()
            log.debug('Fechou corretamente')
            sys.exit()
        except Exception as e:
            log.error(f"Erro ao fechar o programa: {e}")
            self.root.destroy()
            sys.exit()

    def open_ascom_chooser(self):
        try:
            # Cria uma instância do ASCOM Chooser
            chooser = win32com.client.Dispatch("ASCOM.Utilities.Chooser")

            # Abre a caixa de diálogo de seleção de dispositivos ASCOM
            device_id = chooser.Choose("Telescope")

            # Verifica se um dispositivo foi selecionado
            if device_id:
                # verifica se já existe o self.Telescope, se sim, desconecta
                if hasattr(self, 'Telescope'):
                    log.debug(f'Montagem conectado: {self.Telescope} Desconectando...')
                    self.Telescope.Connected = False

                self.device_id = device_id
                # Cria uma instância do dispositivo selecionado
                self.Telescope = win32com.client.Dispatch(device_id)
                self.Telescope.Connected = True
                self.unpark()
                log.debug(f'Conexão realizada com sucesso com driver {device_id}')
                # verifica se já existe o self.comboSpeed, se sim, atualiza os valores
                if hasattr(self, 'comboSpeed'):
                    self.comboSpeed.config(values=self.get_possible_rates())
                try:
                    self.frmConfig.entryTelescope.config(state="normal")
                    self.frmConfig.entryTelescope.delete(0, tk.END)
                    self.frmConfig.entryTelescope.insert(0, self.device_id)
                    self.frmConfig.entryTelescope.config(state="readonly")
                except Exception as e:
                    pass

                # verifica se a classe frmConfig já foi criada e atualiza o campo entry self.telescope_entry
                if hasattr(self, 'frmConfig'):
                    self.frmConfig.telescope_entry.config(state="normal")
                    self.frmConfig.telescope_entry.delete(0, tk.END)
                    self.frmConfig.telescope_entry.insert(0, self.device_id)
                    self.frmConfig.telescope_entry.config(state="readonly")

                return self.Telescope
            else:
                return None
        except Exception as e:
            log.error(f"Erro ao buscar driver do telescópio: {e}")
            messagebox.showerror("Erro", f"Erro ao buscar driver do telescópio: {e}")
            return None


    def show_frmMain(self):
        self.frmMain.pack(fill='both', expand=True)
        self.frmGoto.pack_forget()
        self.frmConfig.pack_forget()

    def show_frmConfig(self):
        self.frmMain.pack_forget()
        self.frmConfig.pack(fill='both', expand=True)
        self.update_visibility(self.frmConfig.canvas_config, self.frmConfig.container)

    def show_frmGoto(self):
        self.frmMain.pack_forget()
        # canvas_goto e container_goto estão dentro da classe frmGoto
        self.frmGoto.pack(fill='both', expand=True)
        self.update_visibility(self.frmGoto.canvas_goto, self.frmGoto.container)

    def get_config(self, section, option):
        """Lê as configurações do arquivo config.ini"""
        config = configparser.ConfigParser()
        if not os.path.exists('config.ini'):
            log.debug("Arquivo de configurações não encontrado")
            return None
        config.read('config.ini')
        log.debug(f"Obtendo configuração {option} do arquivo config.ini")
        if section in config:
            log.debug(f"Seção {section} encontrada")
            if option in config[section]:
                log.debug(f"Configuração {option} encontrada: {config[section][option]}")
                return config[section][option]
        log.debug(f"Configuração {option} não encontrada, retornando None")
        return None

    def del_config(self, section, option):
        """Deleta as configurações do arquivo config.ini"""
        config = configparser.ConfigParser()
        config.read('config.ini')
        if section in config:
            if option in config[section]:
                del config[section][option]
                with open('config.ini', 'w') as configfile:
                    config.write(configfile)
                return True
        return None


    def update_visibility(self, canvas, container):
        #  verifica se canvas está visível e habilita/desabilita o monitoramente da roda do mouse
        viewable = canvas.winfo_height() >= container.winfo_height()
        if viewable:
            canvas.bind_all("<MouseWheel>")
        else:
            canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1*(event.delta/120)), "units"))


# Exemplo de utilização
controller = Controller()
controller.root.mainloop()
