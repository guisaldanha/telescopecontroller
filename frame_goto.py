import tkinter as tk
from tkinter import ttk
from tkinter import font
from tkinter import messagebox
import time
import re
import ephem
import logandprint as log

class frmGoto(tk.Frame):
    def __init__(self, controller, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.controller = controller

        # Configuração da barra de rolagem
        scrollbar_goto = ttk.Scrollbar(self, orient='vertical')
        scrollbar_goto.pack(side='right', fill='y')
        self.canvas_goto = tk.Canvas(self, yscrollcommand=scrollbar_goto.set, highlightthickness=0)
        self.canvas_goto.pack(side='left', fill='both', expand=True)
        scrollbar_goto.config(command=self.canvas_goto.yview)

        # Frame contêiner para widgets de configurações
        self.container = ttk.Frame(self.canvas_goto)
        self.canvas_goto.create_window((0, 0), window=self.container, anchor='nw')

        # Atualização do 'scrollregion' ao alterar o tamanho do contêiner
        self.container.bind('<Configure>', lambda event: self.canvas_goto.configure(scrollregion=self.canvas_goto.bbox('all')))
        # antes de rolar a tela, verifica se o self.canvas_goto está visível
        viewable = self.canvas_goto.winfo_height() >= self.container.winfo_reqheight()
        # se não estiver visível, não permite rolar a tela
        if viewable:
            self.canvas_goto.unbind_all("<MouseWheel>")
        else:
            self.canvas_goto.bind_all("<MouseWheel>", lambda event: self.canvas_goto.yview_scroll(int(-1*(event.delta/120)), "units"))

        # Título
        title_label = ttk.Label(self.container, text='Goto', font=("Segoe UI", 10, "bold"))
        title_label.pack(pady=5)

        # Sistema Solar
        object_frame = ttk.LabelFrame(self.container, text="Sistema Solar")

        # Combobox para seleção do objeto
        object_label = tk.Label(object_frame, text="Objeto")
        object_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.object_combo = ttk.Combobox(object_frame, values=['Sol', 'Lua', 'Mercúrio', 'Vênus', 'Marte', 'Júpiter', 'Saturno', 'Urano', 'Netuno', 'Plutão'], state="readonly", width=25)
        self.object_combo.grid(row=0, column=1, padx=5, pady=5)
        self.object_combo.bind("<<ComboboxSelected>>", lambda event: [self.get_coordinates(), self.object_combo.focus_set()])

        self.txtObjectInfo = tk.Text(object_frame, height=12, width=45, wrap='word', state='disabled', border=0, background=self.cget('background'), font=("Segoe UI", 9))
        self.txtObjectInfo.grid(row=2, column=0, columnspan=2, padx=5)

        object_frame.pack(pady=5, padx=15, fill='both', expand=True)
        object_frame.columnconfigure(0, weight=1)
        object_frame.columnconfigure(1, weight=1)

        frmBottom = tk.Frame(self.container)
        btnVoltar = ttk.Button(frmBottom, text="Voltar", command=controller.show_frmMain)
        btnVoltar.grid(row=2, column=0, padx=5, pady=5)
        btnGoto = ttk.Button(frmBottom, text="Goto", command=self.sendGoto, style="Action.TButton")
        btnGoto.grid(row=2, column=1, padx=5, pady=5)
        frmBottom.pack(pady=5)


    def sendGoto(self):
        try:
            self.controller.unpark()
            ra_decimal, dec_decimal, altitude = self.get_coordinates(alert=False)
            self.controller.Telescope.TargetRightAscension = ra_decimal
            self.controller.Telescope.TargetDeclination = dec_decimal
            if altitude < 0:
                raise Exception("Objeto abaixo do horizonte")
            log.debug(f"Enviando goto para RA: {self.controller.Telescope.TargetRightAscension} DEC: {self.controller.Telescope.TargetDeclination}")
            self.controller.Telescope.Tracking = True
            self.controller.Telescope.SlewToTargetAsync()
            self.controller.gotoInProgress = True
            if self.object_combo.get() == "Sun":
                self.controller.Telescope.TrackingRate = 2
            elif self.object_combo.get() == "Moon":
                self.controller.Telescope.TrackingRate = 1
            else:
                self.controller.Telescope.TrackingRate = 0
            self.controller.show_frmMain()

        except Exception as e:
            error_message = str(e)
            match = re.search(r'SlewError: (.+)', error_message)
            if match:
                error_reason = match.group(1)
            else:
                error_reason = error_message
            log.error(f"Erro ao enviar goto: {error_reason}")
            self.controller.gotoInProgress = False
            messagebox.showerror("Erro", f"Erro ao enviar goto: {error_reason}")
        finally:
            self.controller.root.focus_set()


    def get_coordinates(self, alert=False):
        try:
            obj = self.object_combo.get()
            log.debug(f"Obtenção das coordenadas do objeto: {obj}")
            city = ephem.Observer()
            log.warning(f"Latitude: {self.controller.Telescope.SiteLatitude}, Longitude: {self.controller.Telescope.SiteLongitude}")
            city.lat = str(self.controller.Telescope.SiteLatitude)
            city.lon = str(self.controller.Telescope.SiteLongitude)
            hora_local = str(time.strftime("%Y/%m/%d %H:%M:%S"))
            hora_utc = str(time.strftime("%Y/%m/%d %H:%M:%S", time.gmtime()))
            city.date = str(hora_utc)

            if obj == 'Sol':
                obj_ephen = ephem.Sun(city)
            elif obj == 'Lua':
                obj_ephen = ephem.Moon(city)
            elif obj == 'Mercúrio':
                obj_ephen = ephem.Mercury(city)
            elif obj == 'Vênus':
                obj_ephen = ephem.Venus(city)
            elif obj == 'Marte':
                obj_ephen = ephem.Mars(city)
            elif obj == 'Júpiter':
                obj_ephen = ephem.Jupiter(city)
            elif obj == 'Saturno':
                obj_ephen = ephem.Saturn(city)
            elif obj == 'Urano':
                obj_ephen = ephem.Uranus(city)
            elif obj == 'Netuno':
                obj_ephen = ephem.Neptune(city)
            elif obj == 'Plutão':
                obj_ephen = ephem.Pluto(city)
            else:
                raise ValueError(f"Objeto celeste {obj} não encontrado")

            obj_ephen.compute(city)
            ra, dec = obj_ephen.ra, obj_ephen.dec
            ra_decimal, dec_decimal = obj_ephen.ra * 12 / ephem.pi, obj_ephen.dec * 180 / ephem.pi

            log.debug(f"RA: {ra}, DEC: {dec}, RA decimal: {ra_decimal}, DEC decimal: {dec_decimal}")

            log.debug('A altitude de '+obj+' é: ' + str(obj_ephen.alt))
            log.debug('A longitude do telescópio é ' + str(city.lon) + ' e a latitude é ' + str(city.lat) + ' e a data é ' + str(city.date) + ' e a hora local é ' + str(hora_local) + ' e a hora UTC é ' + str(hora_utc))
            # altitude em decimal
            altitude = obj_ephen.alt * 180 / ephem.pi
            if altitude < 0 and alert:
                messagebox.showwarning("Atenção", obj + " está abaixo do horizonte")

            bold = font.Font(self.txtObjectInfo, self.txtObjectInfo.cget("font"))
            bold.configure(weight="bold")
            self.txtObjectInfo.tag_configure("bold", font=bold)
            self.txtObjectInfo.config(state='normal')
            self.txtObjectInfo.delete('1.0', tk.END)
            self.txtObjectInfo.insert(tk.END, f'Objeto: {obj}\n')
            self.txtObjectInfo.insert(tk.END, f'RA: {ra} DEC: {dec}\n')
            self.txtObjectInfo.insert(tk.END, f'Altitude: ')
            if altitude < 0:
                self.txtObjectInfo.insert(tk.END, str(obj_ephen.alt).replace(":", "°", 1).replace(":", "'", 1), "bold")
            else:
                self.txtObjectInfo.insert(tk.END, str(obj_ephen.alt).replace(":", "°", 1).replace(":", "'", 1))
            self.txtObjectInfo.insert(tk.END, '"\n')
            self.txtObjectInfo.insert(tk.END, f'Magnitude: {obj_ephen.mag}\n')
            self.txtObjectInfo.insert(tk.END, f'Constelação: {ephem.constellation(obj_ephen)[1]}\n')
            self.txtObjectInfo.insert(tk.END, f'Tamanho: {obj_ephen.size:.2f} arcseconds\n')
            self.txtObjectInfo.insert(tk.END, f'Distância do Sol ≈ {obj_ephen.sun_distance:.2f} AU ≈ {self.descricao_numeros(obj_ephen.sun_distance)} km\n')
            self.txtObjectInfo.insert(tk.END, f'Distância da Terra ≈ {obj_ephen.earth_distance:.2f} AU ≈ {self.descricao_numeros(obj_ephen.earth_distance)} km\n')
            self.txtObjectInfo.insert(tk.END, f'Percentual da superfície iluminada: {obj_ephen.phase:.2f}%\n')
            self.txtObjectInfo.insert(tk.END, f'Próximo Nascer: {ephem.localtime(city.next_rising(obj_ephen)).strftime("%d/%m/%Y às %H:%M:%S")}\n')
            self.txtObjectInfo.insert(tk.END, f'Próximo Trânsito: {ephem.localtime(city.next_transit(obj_ephen)).strftime("%d/%m/%Y às %H:%M:%S")}\n')
            self.txtObjectInfo.insert(tk.END, f'Próximo Pôr: {ephem.localtime(city.next_setting(obj_ephen)).strftime("%d/%m/%Y às %H:%M:%S")}')
            self.txtObjectInfo.config(state='disabled')

            return ra_decimal, dec_decimal, altitude
        except Exception as e:
            error = f"Erro ao obter as coordenadas do objeto: {e}"
            log.error(error)
            messagebox.showerror("Erro", error)
            return None, None

    def descricao_numeros(self, ua):
        """Converte a distância em UA para uma descrição mais amigável

        Args:
            ua (float): Distância em UA

        Returns:
            str: Descrição da distância em km
        """
        km = ua * 149597870.7
        if km < 1000:
            return f"{km:.2f}"
        elif km < 1000000:
            return f"{km/1000:.2f} mil"
        elif km < 1000000000:
            return f"{km/1000000:.2f} milhões"
        else:
            return f"{km/1000000000:.2f} bilhões"
