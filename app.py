import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF

# Configuração da página
st.set_page_config(page_title="Geotecnia Pro - Granulometria", layout="wide")

def calcular_classificacao(ll, ip, passa_200):
    # Lógica SUCS
    if passa_200 < 50:
        sucs = "Solo Grosso (Pedregulho/Areia)"
    else:
        if ip > (0.73 * (ll - 20)) and ip > 7: sucs = "CL ou CH (Argila)"
        else: sucs = "ML ou MH (Silte)"
    
    # Lógica AASHTO
    if passa_200 <= 35:
        aashto = "A-1, A-2 ou A-3 (Solo Granular)"
    else:
        aashto = "A-4, A-5, A-6 ou A-7 (Solo Siltoso-Argiloso)"
        
    return sucs, aashto

def classificar_mct(c_prime, d_prime):
    # Lógica Simplificada MCT baseada nos coeficientes c' e d'
    # c' define a inclinação da reta (tipo de solo)
    # d' define a posição (laterítico ou não)
    if c_prime <= 1.0:
        return "Argila Laterítica (LG')" if d_prime > 1.5 else "Argila Não Laterítica (NS')"
    else:
        return "Areia Laterítica (LA')" if d_prime > 1.5 else "Areia Não Laterítica (NA')"

def gerar_pdf(df, sucs, aashto, mct_res, ll, ip):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Relatorio de Caracterizacao de Solos", new_x="LMARGIN", new_y="NEXT", align='C')
    
    # Dados de Atterberg
    pdf.set_font("Helvetica", "", 12)
    pdf.ln(10)
    pdf.cell(0, 10, f"Limite de Liquidez (LL): {ll}%", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f"Indice de Plasticidade (IP): {ip}%", new_x="LMARGIN", new_y="NEXT")
    
    # Classificações
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Classificacoes:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"- SUCS: {sucs}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f"- AASHTO: {aashto}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f"- MCT: {mct_res}", new_x="LMARGIN", new_y="NEXT")
    
    # Tabela de Granulometria
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(60, 10, "Abertura (mm)", border=1)
    pdf.cell(60, 10, "Passante (%)", border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 10)
    for index, row in df.iterrows():
        pdf.cell(60, 10, f"{row['Abertura (mm)']}", border=1)
        pdf.cell(60, 10, f"{row['% Passante Acumulada']:.2f}", border=1)
        pdf.ln()
    
    # O segredo está aqui: converter bytearray para bytes
    return bytes(pdf.output())


# --- INTERFACE STREAMLIT ---
st.title("📊 Analisador de Granulometria NBR 7181 & MCT")

col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("1. Ensaios de Laboratório")
    
    with st.expander("Limites de Atterberg", expanded=True):
        ll = st.number_input("LL (%)", value=35.0)
        lp = st.number_input("LP (%)", value=20.0)
        ip = ll - lp
        st.write(f"**IP calculado:** {ip:.1f}%")

    with st.expander("Método MCT (Ensaios Mini-MCV)", expanded=False):
        st.write("Insira os coeficientes obtidos no ensaio MCT:")
        c_prime = st.number_input("Coeficiente c'", value=1.2)
        d_prime = st.number_input("Coeficiente d'", value=2.0)
        mct_res = classificar_mct(c_prime, d_prime)

    with st.expander("Dados de Peneiramento", expanded=True):
        peso_total = st.number_input("Peso Total Seco (g)", value=1000.0)
        dados_iniciais = pd.DataFrame({
            'Abertura (mm)': [50.8, 25.4, 9.5, 4.75, 2.0, 0.42, 0.075],
            'Peso Retido (g)': [0.0, 0.0, 100.0, 150.0, 200.0, 300.0, 150.0]
        })
        df_input = st.data_editor(dados_iniciais, num_rows="dynamic")

with col2:
    st.subheader("2. Resultados e Curva")
    
    if st.button("Executar Cálculos e Gerar PDF"):
        # Cálculo Granulométrico
        df_input['% Retida'] = (df_input['Peso Retido (g)'] / peso_total) * 100
        df_input['% Retida Acum'] = df_input['% Retida'].cumsum()
        df_input['% Passante Acumulada'] = 100 - df_input['% Retida Acum']
        
        # Plotagem
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df_input['Abertura (mm)'], df_input['% Passante Acumulada'], marker='o', linestyle='-', color='darkblue', linewidth=2)
        ax.set_xscale('log')
        ax.set_xlabel('Diâmetro das Partículas (mm)')
        ax.set_ylabel('Porcentagem Passante (%)')
        ax.set_ylim(0, 105)
        ax.set_title('Curva Granulométrica (NBR 7181)')
        ax.invert_xaxis()
        ax.grid(True, which="both", ls="--", alpha=0.7)
        
        st.pyplot(fig)
        
        # Obter % passando na #200 (0.075mm)
        p200_serie = df_input[df_input['Abertura (mm)'] <= 0.075]['% Passante Acumulada']
        p200 = p200_serie.iloc[-1] if not p200_serie.empty else 0
        
        sucs, aashto = calcular_classificacao(ll, ip, p200)
        
        # Exibição de Métricas
        m1, m2, m3 = st.columns(3)
        m1.success(f"**SUCS:** {sucs}")
        m2.info(f"**AASHTO:** {aashto}")
        m3.warning(f"**MCT:** {mct_res}")
        
        #Gerar e baixar PDF
        try:
            pdf_bytes = gerar_pdf(df_input, sucs, aashto, mct_res, ll, ip)
            st.download_button(
                label="📥 Baixar Relatório Completo (PDF)",
                data=pdf_bytes,
                file_name="relatorio_geotecnico.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")
