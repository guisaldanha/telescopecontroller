import logandprint as log
from tkinter import messagebox
import sys
import threading
import pythoncom
import threading

class UpdateValues(threading.Thread):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.stop_thread = False

    def stop(self):
        self.stop_thread = True
        self.run()

    def run(self):
        if self.stop_thread:
            sys.exit()
        pythoncom.CoInitialize()
        threading.Timer(float(self.controller.cache), self.run).start()
        try:
            self.controller.ra.set(self.convert_ra(self.controller.Telescope.RightAscension or 0.0))
            self.controller.dec.set(self.convert_to_degrees(self.controller.Telescope.Declination or 0.0))
            self.controller.az.set(self.convert_to_degrees(self.controller.Telescope.Azimuth or 0.0))
            self.controller.alt.set(self.convert_to_degrees(self.controller.Telescope.Altitude or 0.0))
            if self.controller.Telescope.Tracking == False:
                self.controller.tracking_rate.set('Off')
            elif self.controller.Telescope.TrackingRate == 0:
                self.controller.tracking_rate.set('Sideral')
            elif self.controller.Telescope.TrackingRate == 1:
                self.controller.tracking_rate.set('Lunar')
            elif self.controller.Telescope.TrackingRate == 2:
                self.controller.tracking_rate.set('Solar')
            elif self.controller.Telescope.TrackingRate == 3:
                self.controller.tracking_rate.set('King rate')
            self.define_status_moviment()
            self.set_find_home_status()
            self.set_park_status()
        except Exception as e:
            self.stop_thread = True
            if not self.controller.Telescope.Connected or 'could not communicate' in str(e):
                error_message = 'A montagem foi desconectada. Uma das causas possíveis é o tempo de atualização que pode está muito baixo.\n' + str(e)
            else:
                error_message = 'Não é possível obter as informações do Telescópio: ' + str(e)
            log.error(error_message)
            messagebox.showerror("Erro crítico", error_message)
            self.controller.root.destroy()
            sys.exit()


    def convert_ra(self, ra):
        """Converts the RA string to the format hh:mm:ss"""
        ra = float(ra)
        h = int(ra)
        m = int((ra - h) * 60)
        s = int((ra - h - m / 60) * 3600)
        return f"{h:02d}h{m:02d}m{s:02d}s"

    def convert_to_degrees(self, value):
        """Converts the value string to degrees format"""
        value = float(value)
        d = int(value)
        m = int(abs((value - d) * 60))
        s = int(abs((value - d) * 3600) % 60)
        return f"{d:02d}°{m:02d}'{s:02d}\""

    def define_status_moviment(self):
        """Define the status of the telescope moviment"""
        telescope = self.controller.Telescope
        if telescope.AtPark:
            moviment = "Estacionado"
        elif telescope.AtHome:
            moviment = "Em casa"
            self.controller.going_home = False
        elif telescope.Slewing:
            if self.controller.manual_slew:
                moviment = "Movimento manual"
            elif self.controller.gotoInProgress:
                moviment = "Buscando objeto"
            elif self.controller.going_home:
                moviment = "Retornando para casa"
            else:
                moviment = "Movendo-se"
        elif telescope.Tracking:
            moviment = "Rastreando"
        else:
            moviment = "Parado"
        self.controller.statusMoviment.set(moviment)
        log.debug(f"Status de movimento: {moviment}")

    def set_find_home_status(self):
        """Set the status of the find home button"""
        at_home = self.controller.Telescope.AtHome
        can_find_home = self.controller.Telescope.CanFindHome
        if at_home or not can_find_home:
            self.controller.btnFindHome.config(state='disabled')
        else:
            self.controller.btnFindHome.config(state='normal')
        if self.controller.going_home:
            self.controller.btnFindHome.config(state='disabled')

    def set_park_status(self):
        """Set the status of the park button"""
        # o botão park_button está na classe frmConfig do arquivo frame_config.py e é chamado no arquivo main.py através do comando self.frmConfig = frmConfig(self)
        btnPark = self.controller.frmConfig.park_button
        btnSetPark = self.controller.frmConfig.set_park_button
        at_park = self.controller.Telescope.AtPark
        can_park = self.controller.Telescope.CanPark
        if at_park or not can_park:
            btnPark.config(state='disabled')
            btnSetPark.config(state='disabled')
        else:
            btnPark.config(state='normal')
            btnSetPark.config(state='normal')
