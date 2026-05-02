import requests
import threading
import time
import random
import os
import argparse
import logging
import urllib3
from collections import deque
from datetime import datetime
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.console import Console, Group
from rich.align import Align
from rich import box
from rich.columns import Columns

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    filename='error.log', 
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

download_links = [
    "https://fsn1-speed.hetzner.com/10GB.bin",
    "http://ipv4.download.thinkbroadband.com/10GB.zip",
    "http://speed.hetzner.de/10GB.bin",
    "http://speedtest.tele2.net/10GB.zip"
]

upload_link = "http://speedtest.tele2.net/upload.php"

class NetworkTester:
    def __init__(self, download_thread_count=4, upload_thread_count=2, max_duration=None, max_data_gb=None):
        self.download_thread_count = download_thread_count
        self.upload_thread_count = upload_thread_count
        self.max_duration = max_duration * 60 if max_duration else None
        self.max_data_bytes = max_data_gb * (1024**3) if max_data_gb else None
        
        self.total_downloaded_bytes = 0
        self.total_uploaded_bytes = 0
        self.current_download_speed = 0
        self.current_upload_speed = 0
        
        self.download_history = deque(maxlen=18)
        self.upload_history = deque(maxlen=18)
        self.current_latency = 0.0
        
        self.is_active = False
        self.test_start_time = 0
        self.thread_lock = threading.Lock()
        self.display_console = Console()
        self.request_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        
        self.working_download_links = []
        self.can_upload = False
        
        self.upload_payload = os.urandom(2 * 1024 * 1024)

    def check_servers(self):
        self.display_console.print("[bold yellow]Sunucular test ediliyor (Health Check)... Lütfen bekleyin.[/]")
        
        for link in download_links:
            try:
                response = requests.get(link, stream=True, timeout=10, headers=self.request_headers, verify=False)
                if response.status_code in [200, 206, 301, 302]:
                    self.working_download_links.append(link)
                response.close()
            except Exception as error_msg:
                logging.error(f"DL Health Check Hatası ({link}): {error_msg}")

        try:
            response = requests.options(upload_link, timeout=10, headers=self.request_headers, verify=False)
            response.raise_for_status()
            self.can_upload = True
        except Exception as error_msg:
            logging.error(f"UL Health Check Hatası ({upload_link}): {error_msg}")

        if not self.working_download_links:
            self.display_console.print("[bold red]Kritik Hata: Erişilebilir download sunucusu bulunamadı![/]")
            exit(1)

        if not self.can_upload:
            self.display_console.print("[bold yellow]Uyarı: Upload sunucusuna ulaşılamıyor, upload işlemleri pas geçilecek.[/]")
            self.upload_thread_count = 0

    def run_download_task(self):
        while self.is_active:
            link = random.choice(self.working_download_links)
            try:
                with requests.get(link, stream=True, headers=self.request_headers, timeout=30, verify=False) as response:
                    response.raise_for_status()
                    for data_chunk in response.iter_content(chunk_size=65536):
                        if not self.is_active:
                            break
                        if data_chunk:
                            with self.thread_lock:
                                self.total_downloaded_bytes += len(data_chunk)
            except Exception as error_msg:
                logging.error(f"Download Hatası ({link}): {error_msg}")
                time.sleep(2)

    def run_upload_task(self):
        while self.is_active and self.can_upload:
            try:
                fake_file = {'file': ('dummy.bin', self.upload_payload)}
                response = requests.post(upload_link, files=fake_file, headers=self.request_headers, timeout=30, verify=False)
                response.raise_for_status()
                with self.thread_lock:
                    self.total_uploaded_bytes += len(self.upload_payload)
            except Exception as error_msg:
                logging.error(f"Upload Hatası: {error_msg}")
                time.sleep(1.5)

    def run_ping_task(self):
        network_session = requests.Session()
        network_session.headers.update(self.request_headers)
        
        while self.is_active:
            link = random.choice(self.working_download_links)
            try:
                ping_start_time = time.perf_counter()
                network_session.get(link, stream=True, timeout=15, verify=False).close()
                calculated_latency = (time.perf_counter() - ping_start_time) * 1000
                with self.thread_lock:
                    self.current_latency = calculated_latency
            except Exception as error_msg:
                logging.error(f"Ping Hatası ({link}): {error_msg}")
            time.sleep(2)

    def create_sparkline_chart(self, history_queue, line_color="white"):
        if not history_queue:
            return f"[{line_color}]-[/]"
        speed_values = list(history_queue)
        graph_ticks = [' ', '▂', '▃', '▄', '▅', '▆', '▇', '█']
        lowest_speed, highest_speed = min(speed_values), max(speed_values)
        
        if highest_speed == lowest_speed:
            sparkline_str = graph_ticks[0] * len(speed_values) if highest_speed == 0 else graph_ticks[3] * len(speed_values)
        else:
            sparkline_str = ""
            for speed_value in speed_values:
                tick_index = int(((speed_value - lowest_speed) / (highest_speed - lowest_speed)) * (len(graph_ticks) - 1))
                sparkline_str += graph_ticks[tick_index]
                
        return f"[{line_color}]{sparkline_str}[/]"

    def create_progress_bar(self, current_val, max_val, label_prefix="", bar_color="cyan"):
        if not max_val: 
            return ""
        completion_ratio = current_val / max_val
        completion_ratio = min(1.0, max(0.0, completion_ratio))
        bar_length = 30
        filled_blocks = int(bar_length * completion_ratio)
        drawn_bar = '█' * filled_blocks + '░' * (bar_length - filled_blocks)
        return f"{label_prefix} [{bar_color}]{drawn_bar}[/] %{completion_ratio*100:.1f}"

    def build_dashboard_ui(self, app_status="Aktif") -> Panel:
        active_seconds = int(time.time() - self.test_start_time) if self.test_start_time else 0
        minutes_passed, seconds_passed = divmod(active_seconds, 60)
        hours_passed, minutes_passed = divmod(minutes_passed, 60)
        formatted_uptime = f"{hours_passed:02d}:{minutes_passed:02d}:{seconds_passed:02d}"

        active_duration_float = time.time() - self.test_start_time if self.test_start_time else 0.1
        
        avg_download_mbps = ((self.total_downloaded_bytes * 8) / 1000000) / active_duration_float if active_duration_float > 0 else 0
        avg_upload_mbps = ((self.total_uploaded_bytes * 8) / 1000000) / active_duration_float if active_duration_float > 0 else 0

        left_info_panel = Panel(
            f"[bold white]İndirme (DL) İş Parçacığı:[/] [bright_cyan]{self.download_thread_count}[/]\n"
            f"[bold white]Yükleme (UL) İş Parçacığı:[/] [bright_cyan]{self.upload_thread_count}[/]",
            title="[dim]Sistem Yapılandırması[/]", border_style="dim", box=box.ROUNDED, expand=True
        )
        
        right_info_panel = Panel(
            f"[bold white]Geçen Süre:[/] [bright_yellow]{formatted_uptime}[/]\n"
            f"[bold white]Ping (Gecikme):[/] [bright_magenta]{self.current_latency:.0f} ms[/]",
            title="[dim]Bağlantı Durumu[/]", border_style="dim", box=box.ROUNDED, expand=True
        )
        
        top_header_columns = Columns([left_info_panel, right_info_panel], expand=True)

        stats_table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold bright_cyan", expand=True)
        stats_table.add_column("Yön", style="bold", width=12)
        stats_table.add_column("Anlık Hız", justify="right", width=15)
        stats_table.add_column("Ortalama Hız", justify="right", style="dim", width=15)
        stats_table.add_column("Aktivite (Son 18s)", justify="center")
        stats_table.add_column("Toplam Transfer", justify="right", width=18)
        
        downloaded_gb = self.total_downloaded_bytes / (1024**3)
        uploaded_gb = self.total_uploaded_bytes / (1024**3)
        
        download_sparkline = self.create_sparkline_chart(self.download_history, "bright_green")
        upload_sparkline = self.create_sparkline_chart(self.upload_history, "bright_magenta")
        
        stats_table.add_row(
            "⬇ DOWNLOAD", 
            f"[bright_green]{self.current_download_speed:.2f} Mbps[/]", 
            f"{avg_download_mbps:.2f} Mbps",
            download_sparkline,
            f"[bold white]{downloaded_gb:.2f} GB[/]"
        )
        stats_table.add_row(
            "⬆ UPLOAD", 
            f"[bright_magenta]{self.current_upload_speed:.2f} Mbps[/]", 
            f"{avg_upload_mbps:.2f} Mbps",
            upload_sparkline,
            f"[bold white]{uploaded_gb:.2f} GB[/]"
        )
        
        indicator_color = "bright_green" if app_status == "Aktif" else "bright_red"
        main_body = Panel(stats_table, title=f"[{indicator_color}]● Canlı Ağ İstatistikleri - {app_status}[/]", border_style="bright_blue", box=box.ROUNDED)

        ui_elements = [top_header_columns, main_body]

        progress_text = ""
        total_transferred_bytes = self.total_downloaded_bytes + self.total_uploaded_bytes
        
        if self.max_duration:
            progress_text += self.create_progress_bar(active_seconds, self.max_duration, "[bold]Süre:[/]", "bright_yellow") + "   "
        if self.max_data_bytes:
            progress_text += self.create_progress_bar(total_transferred_bytes, self.max_data_bytes, "[bold]Kota:[/]", "bright_cyan")
            
        if progress_text:
            progress_panel = Panel(Align.center(progress_text), border_style="dim", box=box.ROUNDED)
            ui_elements.append(progress_panel)

        dashboard_layout = Group(*ui_elements)
        
        return Panel(
            dashboard_layout, 
            title="[bold white]Network Traffic Simulator[/]", 
            subtitle="[dim]Durdurmak için: Ctrl+C | Arka plan hataları error.log dosyasına kaydedilir[/]", 
            border_style="bright_cyan",
            box=box.DOUBLE_EDGE
        )

    def export_session_report(self):
        downloaded_gb = self.total_downloaded_bytes / (1024**3)
        uploaded_gb = self.total_uploaded_bytes / (1024**3)
        active_seconds = int(time.time() - self.test_start_time) if self.test_start_time else 0
        minutes_passed, seconds_passed = divmod(active_seconds, 60)
        hours_passed, minutes_passed = divmod(minutes_passed, 60)
        
        final_report = f"--- Network Traffic Simulator Oturum Raporu ---\n"
        final_report += f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        final_report += f"Çalışma Süresi: {hours_passed:02d}:{minutes_passed:02d}:{seconds_passed:02d}\n"
        final_report += f"Toplam Download: {downloaded_gb:.2f} GB\n"
        final_report += f"Toplam Upload: {uploaded_gb:.2f} GB\n"
        final_report += f"Toplam Harcanan Veri: {(downloaded_gb + uploaded_gb):.2f} GB\n"
        final_report += "---------------------------------------------\n"
        
        try:
            with open("traffic_report.txt", "a", encoding="utf-8") as report_file:
                report_file.write(final_report)
            self.display_console.print("\n[bold bright_green]✓ Oturum raporu kaydedildi: traffic_report.txt[/]")
        except Exception as error_msg:
            self.display_console.print(f"\n[bold bright_red]Rapor kaydedilemedi: {error_msg}[/]")

    def start_test(self):
        self.check_servers()
        
        self.is_active = True
        self.test_start_time = time.time()
        app_status = "Aktif"

        worker_threads = []
        for _ in range(self.download_thread_count):
            worker = threading.Thread(target=self.run_download_task, daemon=True)
            worker.start()
            worker_threads.append(worker)
        
        for _ in range(self.upload_thread_count):
            worker = threading.Thread(target=self.run_upload_task, daemon=True)
            worker.start()
            worker_threads.append(worker)
            
        latency_worker = threading.Thread(target=self.run_ping_task, daemon=True)
        latency_worker.start()
        worker_threads.append(latency_worker)

        self.display_console.clear()
        
        last_time = time.time()
        
        with Live(self.build_dashboard_ui(app_status), refresh_per_second=2, console=self.display_console) as live_display:
            try:
                while self.is_active:
                    previous_dl_bytes, previous_ul_bytes = self.total_downloaded_bytes, self.total_uploaded_bytes
                    time.sleep(1)
                    
                    current_time = time.time()
                    time_elapsed = current_time - last_time
                    last_time = current_time
                    
                    if time_elapsed > 0:
                        dl_speed_mbps = (((self.total_downloaded_bytes - previous_dl_bytes) * 8) / 1000000) / time_elapsed
                        ul_speed_mbps = (((self.total_uploaded_bytes - previous_ul_bytes) * 8) / 1000000) / time_elapsed
                    else:
                        dl_speed_mbps = ul_speed_mbps = 0
                    
                    self.current_download_speed = dl_speed_mbps
                    self.current_upload_speed = ul_speed_mbps
                    
                    self.download_history.append(dl_speed_mbps)
                    self.upload_history.append(ul_speed_mbps)
                    
                    active_duration = current_time - self.test_start_time
                    total_transferred_bytes = self.total_downloaded_bytes + self.total_uploaded_bytes
                    
                    if self.max_duration and active_duration >= self.max_duration:
                        app_status = "Zaman Sınırına Ulaşıldı"
                        self.is_active = False
                    elif self.max_data_bytes and total_transferred_bytes >= self.max_data_bytes:
                        app_status = "Veri Kotası Doldu"
                        self.is_active = False
                        
                    live_display.update(self.build_dashboard_ui(app_status))
            except KeyboardInterrupt:
                self.is_active = False
                app_status = "Kullanıcı Tarafından Kapatıldı"
                live_display.update(self.build_dashboard_ui(app_status))
                time.sleep(1)

        self.export_session_report()

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Network Traffic Simulator")
    arg_parser.add_argument("--dl", type=int, default=4, help="Download thread sayısı")
    arg_parser.add_argument("--ul", type=int, default=2, help="Upload thread sayısı")
    arg_parser.add_argument("--limit", type=float, default=None, help="Toplam veri kotası (GB)")
    arg_parser.add_argument("--time", type=float, default=None, help="Çalışma süresi sınırı (Dakika)")
    
    parsed_args = arg_parser.parse_args()

    network_tester = NetworkTester(
        download_thread_count=parsed_args.dl, 
        upload_thread_count=parsed_args.ul, 
        max_duration=parsed_args.time, 
        max_data_gb=parsed_args.limit
    )
    network_tester.start_test()
