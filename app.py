import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF

# Configuração da página
st.set_page_config(page_title="Geotecnia Pro - Granulometria", layout="wide")

# --- FUNÇÕES DE CÁLCULO TÉCNICO ---

def calcular_ig(p200, ll, ip):
    """Calcula o Índice de Grupo (IG) da AASHTO"""
    a = max(0, min(p200 - 35, 40))
    b = max(0, min(ll - 40, 20))
    c = max(0, min(p200 - 15, 40))
    d = max(0, min(ip - 10, 20))
    ig = a * (0.2 + 0.005 * b) + 0.01 * c * d
    return int(round(ig))

def classificar_aashto(p10, p40, p200, ll, ip):
    """Classificação AASHTO M 145 completa"""
    ig = calcular_ig(p200, ll, ip)
    
    if p200 <= 35:  # Materiais Granulares
        if p200 <= 15 and p40 <= 30 and p10 <= 50: grupo = "A-1-a"
        elif p200 <= 25 and p40 <= 50: grupo = "A-1-b"
        elif p200 <= 10 and p40 <= 51: grupo = "A-3"
        elif ll <= 40: grupo = "A-2-4" if ip <= 10 else "A-2-6"
        else: grupo = "A-2-5" if ip <= 10 else "A-2-7"
        return f"{grupo} (0)" # IG para granulares é sempre 0
    else:  # Materiais Siltoso-Argilosos
        if ll <= 40:
            grupo = "A-4" if ip <= 10 else "A-6"
        else:
            grupo = "A-7-5" if ip <= (ll - 30) else "A-7-6"
        return f"{grupo} ({ig})"

def classificar_sucs(p200, ll, ip, pedregulho, areia):
    """Classificação SUCS (ASTM D2487 / NBR)"""
    if p200 < 50: # Solos Grossos
        tipo = "G" if pedregulho > areia else "S"
        if p200 < 5:
            return f"{tipo}W ou {tipo}P (Requer Cu/Cc)"
        elif p200 > 12:
            sub = "M" if ip < 4 or ip < (0.73 * (ll - 20)) else "C"
            return f"{tipo}{sub}"
        else:
            return f"{tipo}W-{tipo}M (Dupla)"
    else: # Solos Finos
        if ll < 50:
            return "CL" if ip > 7 and ip >= (0.73 * (ll - 20)) else "ML"
        else:
            return "CH" if ip >= (0.73 * (ll - 20)) else "MH"

def classificar_mct(c_prime, d_prime):
    """Classificação MCT Oficial (Nogami & Villibor)"""
    if c_prime < 0.60:
        return "Argila Laterítica (LG')" if d_prime >= 1.5 else "Argila Não Laterítica (NS')"
    elif 0.60 <= c_prime < 1.10:
        return "Solo Limoso Laterítico (LY')" if d_prime >= 1.5 else "Solo Limoso Não Laterítico (NA')"
    elif 1.10 <= c_prime < 1.50:
        return "Areia Argilosa Laterítica (LA')" if d_prime >= 1.5 else "Solo Arenoso Não Laterítico (NA')"
    else:
        return "Areia Quartzosa (AQ)"

def gerar_pdf(df, sucs, aashto, mct_res, ll, ip):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Relatorio de Ensaio Geotecnico", new_x="LMARGIN", new_y="NEXT", align='C')
    
    pdf.set_font("Helvetica", "", 12)
    pdf.ln(10)
    pdf.cell(0, 8, f"Limite de Liquidez (LL): {ll}%", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Indice de Plasticidade (IP): {ip}%", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Classificacoes Finais:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, f"- SUCS: {sucs}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"- AASHTO: {aashto}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"- MCT: {mct_res}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(45, 10, "Abertura (mm)", border=1, align='C')
    pdf.cell(45, 10, "Peso Retido (g)", border=1, align='C')
    pdf.cell(45, 10, "Passante (%)", border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Helvetica", "", 10)
    for _, row in df.iterrows():
        pdf.cell(45, 10, f"{row['Abertura (mm)']}", border=1, align='C')
        pdf.cell(45, 10, f"{row['Peso Retido (g)']}", border=1, align='C')
        pdf.cell(45, 10, f"{row['% Passante Acumulada']:.2f}", border=1, align='C')
        pdf.ln()
    
    return bytes(pdf.output())

# --- INTERFACE ---

st.title("🚜 Sistema Integrado de Classificação de Solos")
st.markdown("---")

col1, col2 = st.columns([1.2, 2])

with col1:
    st.subheader("📋 Dados de Entrada")
    
    with st.expander("Fração Fina (Atterberg)", expanded=True):
        ll = st.number_input("LL (%)", value=35.0, step=0.1)
        lp = st.number_input("LP (%)", value=20.0, step=0.1)
        ip = ll - lp
        st.info(f"IP: {ip:.1f}%")

    with st.expander("Ensaios MCT (Mini-MCV)", expanded=True):
        c_p = st.number_input("Coeficiente c'", value=1.2, format="%.2f")
        d_p = st.number_input("Coeficiente d'", value=2.0, format="%.2f")

    with st.expander("Peneiramento (NBR 7181)", expanded=True):
        p_total = st.number_input("Peso Total Seco (g)", value=1000.0)
        df_base = pd.DataFrame({
            'Abertura (mm)': [50.8, 25.4, 9.5, 4.75, 2.0, 0.42, 0.075],
            'Peso Retido (g)': [0.0, 0.0, 10.0, 40.0, 200.0, 400.0, 150.0]
        })
        df_edit = st.data_editor(df_base, num_rows="dynamic")

with col2:
    st.subheader("📈 Análise e Resultados")
    
    if st.button("CALCULAR TUDO", use_container_width=True):
        # Processamento Granulométrico
        df_edit['% Ret'] = (df_edit['Peso Retido (g)'] / p_total) * 100
        df_edit['% Passante Acumulada'] = 100 - df_edit['% Ret'].cumsum()
        
        # Plotagem Semilog
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df_edit['Abertura (mm)'], df_edit['% Passante Acumulada'], 'o-', color='#1f77b4', lw=2)
        ax.set_xscale('log')
        ax.set_xlabel('Diâmetro das Partículas (mm)')
        ax.set_ylabel('Passante Acumulado (%)')
        ax.grid(True, which="both", ls="-", alpha=0.5)
        ax.set_xlim(max(df_edit['Abertura (mm)']), 0.001)
        ax.set_ylim(0, 105)
        st.pyplot(fig)

        # Extração de frações para Classificação
        def get_p(mm):
            res = df_edit[df_edit['Abertura (mm)'] <= mm]['% Passante Acumulada']
            return res.iloc[0] if not res.empty else 0

        p10, p40, p200 = get_p(2.0), get_p(0.42), get_p(0.075)
        pedregulho = 100 - get_p(4.75)
        areia = get_p(4.75) - p200

        # Resultados
        res_aashto = classificar_aashto(p10, p40, p200, ll, ip)
        res_sucs = classificar_sucs(p200, ll, ip, pedregulho, areia)
        res_mct = classificar_mct(c_p, d_p)

        c1, c2, c3 = st.columns(3)
        c1.metric("AASHTO", res_aashto)
        c2.metric("SUCS", res_sucs)
        c3.metric("MCT", res_mct)

        # PDF
        pdf_file = gerar_pdf(df_edit, res_sucs, res_aashto, res_mct, ll, ip)
        st.download_button("📂 Baixar Relatório PDF", pdf_file, "relatorio.pdf", "application/pdf")
