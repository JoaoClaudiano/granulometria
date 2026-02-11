import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF
from scipy.interpolate import interp1d
import base64

st.set_page_config(page_title="Geotecnia Pro - Universitário", layout="wide")

# --- FUNÇÕES DE APOIO ---
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
        else: return "A-5" if ip <= 10 else "A-7"

def gerar_pdf(df, res):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Relatório de Ensaio de Granulometria", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    for k, v in res.items():
        pdf.cell(200, 10, f"{k}: {v}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACE ---
st.title("🔬 Caracterização de Solos - Acadêmico")

with st.sidebar:
    st.header("📊 Parâmetros MCT")
    st.write("Tabela de Apoio:")
    mct_data = pd.DataFrame({
        "Grupo": ["Latossolos", "Areias", "Argilas"],
        "Aptidão": ["Excelente", "Boa", "Pobre"]
    })
    st.table(mct_data)
    
    st.header("📂 Importar")
    arquivo = st.file_uploader("CSV ou Excel", type=['csv', 'xlsx'])

col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("📥 Dados de Entrada")
    massa_total = st.number_input("Massa Seca Real (g)", value=1000.0, help="Use a massa exata pesada após a estufa.")
    ll = st.number_input("LL (%)", value=35.0)
    lp = st.number_input("LP (%)", value=20.0)
    ip = ll - lp

    if arquivo:
        df_base = pd.read_csv(arquivo) if arquivo.name.endswith('.csv') else pd.read_excel(arquivo)
    else:
        df_base = pd.DataFrame({
            'Abertura (mm)': [50.8, 4.75, 2.0, 0.42, 0.075],
            'Peso Retido (g)': [0.0, 150.0, 250.0, 300.0, 100.0]
        })
    df_edit = st.data_editor(df_base, num_rows="dynamic")
    soma_retida = df_edit['Peso Retido (g)'].sum()
    st.caption(f"Soma Retida: {soma_retida}g | Erro: {abs(soma_retida-massa_total):.1f}g")

with col2:
    if st.button("🚀 CALCULAR E GERAR RELATÓRIO", use_container_width=True):
        df_edit['% Passante'] = 100 - (df_edit['Peso Retido (g)'].cumsum() / massa_total * 100)
        
        # Gráfico
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(df_edit['Abertura (mm)'], df_edit['% Passante'], 'o-')
        ax.set_xscale('log')
        ax.invert_xaxis()
        ax.grid(True, which="both", alpha=0.3)
        st.pyplot(fig)
        
        # Lógica de Classificação
        cu, cc, d10 = calcular_diametros(df_edit)
        p200 = df_edit[df_edit['Abertura (mm)'] <= 0.075]['% Passante'].iloc[0] if any(df_edit['Abertura (mm)'] <= 0.075) else 0
        p4 = df_edit[df_edit['Abertura (mm)'] <= 4.75]['% Passante'].iloc[0] if any(df_edit['Abertura (mm)'] <= 4.75) else 0
        pedregulho = 100 - p4
        areia = p4 - p200
        
        sucs = classificar_sucs(p200, ll, ip, pedregulho, areia, cu, cc)
        aashto = classificar_aashto(p200, ll, ip)
        
        # Display Resultados
        res_dict = {"SUCS": sucs, "AASHTO": aashto, "IP": ip, "Cu": cu, "Cc": cc}
        c1, c2, c3 = st.columns(3)
        c1.metric("SUCS", sucs)
        c2.metric("AASHTO", aashto)
        c3.metric("IP", f"{ip}%")
        
        # PDF
        pdf_bytes = gerar_pdf(df_edit, res_dict)
        st.download_button("📥 Baixar Relatório PDF", data=pdf_bytes, file_name="ensaio_solos.pdf", mime="application/pdf")

        with st.expander("📚 Memorial de Cálculo"):
            st.write(f"1. IP = {ll} - {lp} = {ip}")
            st.write(f"2. Frações: Pedregulho {pedregulho:.1f}%, Areia {areia:.1f}%, Finos {p200:.1f}%")
