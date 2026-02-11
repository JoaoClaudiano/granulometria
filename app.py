import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF
from scipy.interpolate import interp1d
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Geotecnia Pro 3.1", layout="wide")

# --- FUNÇÕES TÉCNICAS ---
def calcular_diametros(df):
    try:
        df_sorted = df.sort_values('Abertura (mm)')
        x = df_sorted['% Passante'].values
        y = df_sorted['Abertura (mm)'].values
        f = interp1d(x, np.log10(y), bounds_error=False, fill_value="extrapolate")
        d10, d30, d60 = 10**f(10), 10**f(30), 10**f(60)
        cu = d60 / d10 if d10 > 0 else 0
        cc = (d30**2) / (d60 * d10) if (d60 * d10) > 0 else 0
        return round(cu, 2), round(cc, 2), round(d10, 3)
    except: return 0, 0, 0

def classificar_sucs(p200, ll, ip, pedregulho, areia, cu, cc):
    if p200 < 50:
        pref = "G" if pedregulho > areia else "S"
        if p200 < 5:
            grad = "W" if (pref=="G" and cu > 4 and 1 <= cc <= 3) or (pref=="S" and cu > 6 and 1 <= cc <= 3) else "P"
            return f"{pref}{grad}"
        elif p200 > 12:
            suf = "C" if ip > 7 and ip >= (0.73*(ll-20)) else "M"
            return f"{pref}{suf}"
        else: return f"{pref}W-{pref}M"
    else:
        tipo = "C" if ip > 7 and ip >= (0.73*(ll-20)) else "M"
        comp = "L" if ll < 50 else "H"
        return f"{tipo}{comp}"

def classificar_aashto(p200, ll, ip):
    if p200 <= 35:
        if p200 <= 15: return "A-1-a"
        if p200 <= 25: return "A-1-b"
        return "A-3" if ll == 0 else "A-2"
    else:
        if ll < 40: return "A-4" if ip <= 10 else "A-6"
        else: return "A-7-5" if ip <= (ll - 30) else "A-7-6"

def gerar_pdf(res_gerais):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Relatorio de Caracterizacao Geotecnica", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for k, v in res_gerais.items():
        pdf.cell(200, 10, f"{k}: {v}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACE ---
st.title("🔬 Sistema Integrado de Geotecnia")

with st.sidebar:
    st.header("⚙️ Opções")
    mostrar_zonas = st.toggle("Zonas Didáticas (Gráfico)", value=True)
    arquivo = st.file_uploader("Subir Dados (.csv ou .xlsx)", type=['csv', 'xlsx'])

col_in, col_out = st.columns([1, 1.8])

with col_in:
    st.subheader("📥 Entrada de Dados")
    with st.expander("📌 Índices e Massa", expanded=True):
        m_seca = st.number_input("Massa Seca Total (g)", value=1000.0)
        ll = st.number_input("Limite de Liquidez - LL (%)", value=35.0)
        lp = st.number_input("Limite de Plasticidade - LP (%)", value=20.0)
        ip = ll - lp
    
    with st.expander("🌴 Classificação MCT (Manual)", expanded=False):
        mct_man = st.text_input("Resultado MCT", "Ex: LG'")
        st.caption("A classificação MCT requer ensaios de compactação Mini-Proctor.")

    if arquivo:
        df_base = pd.read_csv(arquivo) if arquivo.name.endswith('.csv') else pd.read_excel(arquivo)
    else:
        df_base = pd.DataFrame({'Abertura (mm)': [50.8, 19.0, 4.75, 2.0, 0.42, 0.075], 'Peso Retido (g)': [0.0, 100.0, 150.0, 200.0, 300.0, 150.0]})
    
    df_edit = st.data_editor(df_base, num_rows="dynamic", key="geo_editor")

with col_out:
    if st.button("🚀 PROCESSAR ANÁLISE COMPLETA", use_container_width=True):
        df_edit['% Passante'] = 100 - (df_edit['Peso Retido (g)'].cumsum() / m_seca * 100)
        
        # Gráfico
        fig, ax = plt.subplots(figsize=(10, 5))
        if mostrar_zonas:
            ax.axvspan(0.001, 0.075, color='gray', alpha=0.1)
            ax.axvspan(0.075, 4.75, color='blue', alpha=0.05)
            ax.axvspan(4.75, 76.2, color='green', alpha=0.05)
            ax.text(0.01, 95, "FINOS", fontsize=9, alpha=0.4)
            ax.text(0.5, 95, "AREIA", fontsize=9, alpha=0.4)
            ax.text(20, 95, "PEDREGULHO", fontsize=9, alpha=0.4)

        ax.plot(df_edit['Abertura (mm)'], df_edit['% Passante'], 'o-', color='#1a5276', lw=2)
        ax.set_xscale('log'); ax.invert_xaxis()
        ax.set_xlim(100, 0.001); ax.set_ylim(0, 105)
        ax.grid(True, which="both", alpha=0.2)
        st.pyplot(fig)

        # Cálculos e Classificações
        cu, cc, d10 = calcular_diametros(df_edit)
        p200 = df_edit[df_edit['Abertura (mm)'] <= 0.075]['% Passante'].iloc[0] if any(df_edit['Abertura (mm)'] <= 0.075) else 0
        p4 = df_edit[df_edit['Abertura (mm)'] <= 4.75]['% Passante'].iloc[0] if any(df_edit['Abertura (mm)'] <= 4.75) else 0
        sucs = classificar_sucs(p200, ll, ip, (100-p4), (p4-p200), cu, cc)
        aashto = classificar_aashto(p200, ll, ip)

        # Painel de Resultados
        st.subheader("🏁 Classificações Encontradas")
        r1, r2, r3 = st.columns(3)
        r1.info(f"**SUCS**\n\n### {sucs}")
        r2.success(f"**AASHTO**\n\n### {aashto}")
        r3.warning(f"**MCT**\n\n### {mct_man if mct_man else 'N/A'}")

        # Tabela de Comparação/Resumo
        st.markdown("### 📊 Tabela de Propriedades")
        res_resumo = pd.DataFrame({
            "Propriedade": ["D10 (mm)", "Cu", "Cc", "Finos (#200)", "Pedregulho", "Areia", "IP (%)"],
            "Valor": [d10, cu, cc, f"{p200:.1f}%", f"{(100-p4):.1f}%", f"{(p4-p200):.1f}%", f"{ip:.1f}%"]
        })
        st.table(res_resumo)

        # PDF
        dados_pdf = {
            "Massa Total": f"{m_seca}g", "LL": f"{ll}%", "LP": f"{lp}%", "IP": f"{ip}%",
            "SUCS": sucs, "AASHTO": aashto, "MCT": mct_man, "Cu": cu, "Cc": cc
        }
        pdf_export = gerar_pdf(dados_pdf)
        st.download_button("📥 Baixar Relatório Completo (PDF)", data=pdf_export, file_name="relatorio_geotecnico.pdf", mime="application/pdf", use_container_width=True)
