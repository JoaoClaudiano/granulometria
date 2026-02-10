import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF
import base64

# Configuração da página
st.set_page_config(page_title="Geotecnia Pro - Granulometria", layout="wide")

def calcular_classificacao(ll, ip, passa_200):
    # Lógica Simplificada SUCS
    if passa_200 < 50:
        sucs = "Solo Grosso (Pedregulho/Areia)"
    else:
        if ip > (0.73 * (ll - 20)) and ip > 7: sucs = "CL ou CH (Argila)"
        else: sucs = "ML ou MH (Silte)"
    
    # Lógica Simplificada AASHTO
    if passa_200 <= 35:
        aashto = "A-1, A-2 ou A-3 (Solo Granular)"
    else:
        aashto = "A-4, A-5, A-6 ou A-7 (Solo Siltoso-Argiloso)"
        
    return sucs, aashto

def gerar_pdf(df, sucs, aashto, ll, ip):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Relatorio de Caracterizacao de Solos", ln=True, align='C')
    
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    pdf.cell(200, 10, f"Limite de Liquidez (LL): {ll}%", ln=True)
    pdf.cell(200, 10, f"Indice de Plasticidade (IP): {ip}%", ln=True)
    pdf.ln(5)
    pdf.cell(200, 10, f"Classificacao SUCS: {sucs}", ln=True)
    pdf.cell(200, 10, f"Classificacao AASHTO: {aashto}", ln=True)
    
    # Tabela de dados
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(40, 10, "Abertura (mm)", border=1)
    pdf.cell(40, 10, "Passante (%)", border=1)
    pdf.ln()
    pdf.set_font("Arial", "", 10)
    for index, row in df.iterrows():
        pdf.cell(40, 10, str(row['Abertura (mm)']), border=1)
        pdf.cell(40, 10, f"{row['% Passante Acumulada']:.2f}", border=1)
        pdf.ln()
    
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACE STREAMLIT ---
st.title("📊 Analisador de Granulometria NBR 7181")
st.markdown("Insira os dados do ensaio de peneiramento e limites de Atterberg abaixo.")

col1, col2 = st.columns([1, 2])

with col1:
    st.header("1. Limites de Atterberg")
    ll = st.number_input("Limite de Liquidez (LL %)", min_value=0.0, value=30.0)
    lp = st.number_input("Limite de Plasticidade (LP %)", min_value=0.0, value=20.0)
    ip = ll - lp
    st.info(f"Índice de Plasticidade (IP): {ip:.1f}%")

    st.header("2. Peneiramento")
    peso_total = st.number_input("Peso Total da Amostra (g)", min_value=0.1, value=1000.0)
    
    # Tabela editável
    dados_iniciais = pd.DataFrame({
        'Abertura (mm)': [9.5, 4.75, 2.0, 0.42, 0.075],
        'Peso Retido (g)': [0.0, 50.0, 150.0, 300.0, 200.0]
    })
    df_input = st.data_editor(dados_iniciais, num_rows="dynamic")

with col2:
    st.header("3. Resultados e Gráfico")
    
    if st.button("Calcular e Gerar Gráfico"):
        # Cálculos de Granulometria
        df_input['% Retida'] = (df_input['Peso Retido (g)'] / peso_total) * 100
        df_input['% Retida Acumulada'] = df_input['% Retida'].cumsum()
        df_input['% Passante Acumulada'] = 100 - df_input['% Retida Acumulada']
        
        # Plotagem
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(df_input['Abertura (mm)'], df_input['% Passante Acumulada'], marker='o', color='blue')
        ax.set_xscale('log')
        ax.set_xlabel('Diâmetro das Partículas (mm)')
        ax.set_ylabel('Porcentagem Passante (%)')
        ax.set_title('Curva Granulométrica')
        ax.invert_xaxis()
        ax.grid(True, which="both", ls="-")
        
        
        st.pyplot(fig)
        
        # Classificações
        p200 = df_input[df_input['Abertura (mm)'] <= 0.075]['% Passante Acumulada'].min()
        sucs, aashto = calcular_classificacao(ll, ip, p200)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("SUCS", sucs)
        c2.metric("AASHTO", aashto)
        c3.metric("MCT", "Pendente Mini-MCV")
        
        # PDF
        pdf_bytes = gerar_pdf(df_input, sucs, aashto, ll, ip)
        st.download_button(label="📥 Baixar Relatório em PDF",
                         data=pdf_bytes,
                         file_name="relatorio_solos.pdf",
                         mime="application/pdf")
