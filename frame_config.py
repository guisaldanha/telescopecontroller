import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import configparser
from tooltip import ToolTip
import os
import sys
import logandprint as log

class frmConfig(tk.Frame):
    def __init__(self, controller, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.controller = controller

        # Configuração da barra de rolagem
        scrollbar_config = ttk.Scrollbar(self, orient='vertical')
        scrollbar_config.pack(side='right', fill='y')
        self.canvas_config = tk.Canvas(self, yscrollcommand=scrollbar_config.set, highlightthickness=0)
        self.canvas_config.pack(side='left', fill='both', expand=True)
        scrollbar_config.config(command=self.canvas_config.yview)

        # Frame contêiner para widgets de configurações
        self.container = ttk.Frame(self.canvas_config)
        self.canvas_config.create_window((0, 0), window=self.container, anchor='nw')

        # Atualização do 'scrollregion' ao alterar o tamanho do contêiner
        self.container.bind('<Configure>', lambda event: self.canvas_config.configure(scrollregion=self.canvas_config.bbox('all')))
        # antes de rolar a tela, verifica se o self.canvas_config está visível
        viewable = self.canvas_config.winfo_height() >= self.container.winfo_reqheight()
        # se não estiver visível, não permite rolar a tela
        if viewable:
            self.canvas_config.unbind_all("<MouseWheel>")
        else:
            self.canvas_config.bind_all("<MouseWheel>", lambda event: self.canvas_config.yview_scroll(int(-1*(event.delta/120)), "units"))

        # Título
        title_label = ttk.Label(self.container, text='Configurações', font=("Segoe UI", 10, "bold"))
        title_label.pack(pady=5)

        # Configurações do driver
        communication_frame = tk.LabelFrame(self.container, text="Configurações do driver")

        # Botão para buscar o driver do telescópio
        find_telescope_button = ttk.Button(communication_frame, text="Buscar Driver do Telescópio", command=controller.open_ascom_chooser)
        find_telescope_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        # Entrada para o telescópio
        telescope_label = tk.Label(communication_frame, text="Telescópio")
        telescope_label.grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.telescope_entry = tk.Entry(communication_frame, width=30)
        self.telescope_entry.grid(row=2, column=1, padx=5, pady=5)
        if controller.device_id:
            self.telescope_entry.insert(0, controller.device_id)
        self.telescope_entry.config(state="readonly", readonlybackground="white")

        # Entrada para o tempo de atualização
        updating_label = tk.Label(communication_frame, text="Tempo atualização")
        updating_label.grid(row=3, column=0, padx=5, pady=5, sticky="e")
        ToolTip(updating_label, "Tempo em segundos para atualização dos valores dos eixos e sincronização dos valores do onstep. Quanto menor for esse número, mais rápida será a atualização e mais requisições ao onstep serão feitas.", width=40)
        self.updating_entry = tk.Entry(communication_frame, width=15)
        self.updating_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        self.updating_entry.insert(0, controller.cache)

        # Botão "OK" para confirmar a entrada de atualização
        save_driver = ttk.Button(communication_frame, text="Salvar", command=self.save_driver_config, width=8)
        save_driver.grid(row=4, column=0, padx=5, pady=5, columnspan=2)

        communication_frame.pack(pady=5, padx=15, fill='both')
        communication_frame.columnconfigure(0, weight=1)
        communication_frame.columnconfigure(1, weight=0)  # Nova coluna para o botão, não precisa expandir

        # Movimentação dos eixos
        axis_frame = tk.LabelFrame(self.container, text="Movimentação dos Eixos")

        # Checkbox para inverter Leste/Oeste
        self.invert_ew_var = tk.BooleanVar()
        invert_ew_label = tk.Label(axis_frame, text="Inverter Leste/Oeste")
        invert_ew_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        ToolTip(invert_ew_label, "Inverte a direção dos eixos Leste/Oeste", width=40)
        invert_ew_label.bind("<Button-1>", lambda event: self.invert_ew_var.set(not self.invert_ew_var.get()))
        if controller.get_config('AXIS', 'invert_ew') == 'True':
            self.invert_ew_var.set(True)
        invert_ew_check = tk.Checkbutton(axis_frame, variable=self.invert_ew_var)
        invert_ew_check.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        # monitora se o valor de invert_ew_var foi alterado
        self.invert_ew_var.trace_add('write', lambda *args: self.save_invert_axis('ew'))

        # Checkbox para inverter Norte/Sul
        self.invert_ns_var = tk.BooleanVar()
        invert_ns_label = tk.Label(axis_frame, text="Inverter Norte/Sul")
        invert_ns_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        ToolTip(invert_ns_label, "Inverte a direção dos eixos Norte/Sul", width=40)
        invert_ns_label.bind("<Button-1>", lambda event: self.invert_ns_var.set(not self.invert_ns_var.get()))
        if controller.get_config('AXIS', 'invert_ns') == 'True':
            self.invert_ns_var.set(True)
        invert_ns_check = tk.Checkbutton(axis_frame, variable=self.invert_ns_var)
        invert_ns_check.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        # monitora se o valor de invert_ns_var foi alterado
        self.invert_ns_var.trace_add('write', lambda *args: self.save_invert_axis('ns'))

        axis_frame.pack(pady=5, padx=15, fill='both')
        axis_frame.columnconfigure(0, weight=1)
        axis_frame.columnconfigure(1, weight=2)

        # Comando park e set park
        park_frame = tk.LabelFrame(self.container, text="Estacionamento")

        # Botão para estacionar o telescópio
        self.park_button = ttk.Button(park_frame, text="Estacionar", command=self.park)
        self.park_button.grid(row=0, column=0, padx=5, pady=5)

        # Botão para setar o estacionamento
        self.set_park_button = ttk.Button(park_frame, text="Setar Estacionamento", command=self.set_park_position)
        self.set_park_button.grid(row=0, column=1, padx=5, pady=5)
        ToolTip(self.set_park_button, "Seta a posição atual do telescópio como a posição de estacionamento. O telescópio irá se mover para essa posição ao ser estacionado.", width=20)

        park_frame.pack(pady=5, padx=15, fill='both')
        park_frame.columnconfigure(0, weight=1)
        park_frame.columnconfigure(1, weight=1)

        # Botões
        bottom_frame = tk.Frame(self.container)
        back_button = ttk.Button(bottom_frame, text="Voltar", command=self.back, width=15)
        back_button.grid(column=0, row=0, padx=5, pady=5)
        bottom_frame.pack(pady=5)

        # Botão para resetar as configurações
        reset_button = ttk.Button(self.container, text="Resetar Configurações e Reiniciar o Programa", command=self.reset_config)
        reset_button.pack(pady=15)

        # Ajusta a barra de rolagem para o topo
        self.canvas_config.yview_moveto(0)

    def save_driver_config(self):
        try:
            log.debug("Salvando configurações do driver")
            cache = float(self.updating_entry.get().replace(',', '.'))
            if cache < 0.1:
                raise ValueError("O tempo de atualização deve ser menor que 0.1")
            self.set_config('COMMUNICATION', 'driver', self.telescope_entry.get())
            self.controller.cache = cache
            self.set_config('COMMUNICATION', 'cache', cache)
            self.back()
        except Exception as e:
            log

    def save_invert_axis(self, axis):
        log.debug(f"Salvando configurações do eixo {axis}")
        if axis == 'ew':
            self.set_config('AXIS', 'invert_ew', self.invert_ew_var.get())
            log.debug(f"Invertendo eixo Leste/Oeste: {self.invert_ew_var.get()}")
        elif axis == 'ns':
            self.set_config('AXIS', 'invert_ns', self.invert_ns_var.get())
            log.debug(f"Invertendo eixo Norte/Sul: {self.invert_ns_var.get()}")
        self.back()


    def set_config(self, section, option, value):
        """Salva as configurações no arquivo config.ini"""
        value = str(value)
        if value == '':
            return
        config = configparser.ConfigParser()
        config.read('config.ini')
        if section in config:
            config[section][option] = value
        else:
            config[section] = {option: value}
        with open('config.ini', 'w') as configfile:
            config.write(configfile)

    def park(self):
        try:
            self.controller.Telescope.Park()
            self.back()
        except Exception as e:
            log.error(f"Erro ao estacionar telescópio: {e}")
            messagebox.showerror("Erro", f"Erro ao estacionar telescópio: {e}")

    def set_park_position(self):
        try:
            confirm = messagebox.askyesno("Setar posição de estacionamento", "Deseja setar a posição de estacionamento como a posição atual?")
            if not confirm:
                return
            log.debug("Setando posição de estacionamento")
            self.controller.Telescope.SetPark()
            messagebox.showinfo("Estacionamento", "Posição de estacionamento setada com sucesso.\n\nO telescópio irá se mover para essa posição ao ser estacionado.")
            self.back()
        except Exception as e:
            log.error(f"Erro ao setar posição de estacionamento: {e}")
            messagebox.showerror("Erro", f"Erro ao setar posição de estacionamento: {e}")

    def back(self):
        self.canvas_config.yview_moveto(0)
        self.controller.show_frmMain()

    def reset_config(self):
        """Reseta as configurações do programa e reinicia o programa."""
        try:
            if os.path.exists('config.ini'):
                os.remove('config.ini')
            messagebox.showinfo("Configurações", "Configurações resetadas. O programa será reiniciado.")
            self.controller.root.destroy()
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as e:
            log.error(f"Erro ao resetar as configurações: {e}")
            messagebox.showerror("Erro", f"Erro ao resetar as configurações: {e}")
