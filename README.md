<div align="center">

# 🌐 Network Traffic Simulator 🚀

**Ağ bağlantınızı test edin, sınırları zorlayın ve gecikmeleri anlık izleyin.**

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.7+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Rich_Terminal-13.0+-purple?style=for-the-badge&logo=gnu-bash&logoColor=white" alt="Rich">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

[Özellikler](#-özellikler) • [Kurulum](#-kurulum) • [Kullanım](#-kullanım) • [Uyarılar](#-uyarılar)

</div>

<br>

> **💡 Nedir Bu Araç?**
> Arka planda belirlediğiniz sayıda eşzamanlı indirme (download) ve yükleme (upload) işlemi başlatarak ağınızı satüre eden, oluşan ping dalgalanmalarını ve hız limitlerini gerçek zamanlı, şık bir terminal paneli üzerinden sunan çok iş parçacıklı (multi-threaded) bir Python CLI aracıdır.

<br>

## ✨ Özellikler

<table>
  <tr>
    <td><b>🚀 Multi-threading</b></td>
    <td>Eşzamanlı download ve upload işlemleri ile hattı tam kapasite kullanma.</td>
  </tr>
  <tr>
    <td><b>📊 Canlı Dashboard</b></td>
    <td>Anlık hız, ortalama hız ve mini grafikler (sparklines) içeren modern terminal arayüzü.</td>
  </tr>
  <tr>
    <td><b>⚡ Ping (Gecikme) Ölçümü</b></td>
    <td>Yük altındayken ağınızın bufferbloat durumunu ve tepki süresini anlık olarak izleme.</td>
  </tr>
  <tr>
    <td><b>🩺 Otomatik Sağlık Kontrolü</b></td>
    <td>Test başlamadan önce hedef sunucuların erişilebilirliğini otomatik test eder.</td>
  </tr>
</table>

<details>
<summary><b>Diğer Özellikleri Görmek İçin Tıklayın...</b></summary>
<br>
<ul>
  <li><b>🛑 Kotalı Test İmkanı:</b> İstediğiniz zaman süresi (Dakika) veya veri hacmi (GB) sınırına ulaşıldığında testi otomatik durdurma.</li>
  <li><b>📁 Detaylı Raporlama:</b> Oturum kapandığında tüketilen veriyi ve süreyi <code>traffic_report.txt</code> dosyasına kaydeder.</li>
  <li><b>🐛 Arka Plan Hata Günlüğü:</b> Bağlantı kopmaları ve zaman aşımları sessizce <code>error.log</code> dosyasına yazılır.</li>
</ul>
</details>

<br>

## 🛠️ Kurulum

Terminalinizi açın ve aşağıdaki adımları sırasıyla uygulayın:

```bash
# 1. Depoyu bilgisayarınıza klonlayın
git clone https://github.com/tmertarin/network-traffic-simulator.git

# 2. Klasörün içine girin
cd network-traffic-simulator

# 3. Gerekli Python kütüphanelerini kurun
pip install -r requirements.txt
