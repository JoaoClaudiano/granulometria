import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF

st.set_page_config(page_title="Geotecnia Pro - NBR 7181", layout="wide")

# --- LÓGICA TÉCNICA REFINADA ---

def obter_criterios(p200, ll, ip, pedregulho, areia, p10, p40, c_p, d_p):
    """Gera a memória de cálculo para o usuário"""
    sucs_msg = f"Baseado em {p200:.1f}% de finos (< 0,075mm). "
    if p200 < 50:
        sucs_msg += f"Solo Grosso ({'Pedregulho' if pedregulho > areia else 'Areia'})."
    else:
        sucs_msg += f"Solo Fino com LL={ll}% e IP={ip}%."

    aashto_msg = f"Grupo definido por p200={p200:.1f}%, LL={ll}% e IP={ip}%."
    
    mct_msg = f"Classificação Tropical via coeficientes c'={c_p} e d'={d_p}."
    
    return sucs_msg, aashto_msg, mct_msg

def classificar_aashto(p10, p40, p200, ll, ip):
    a = max(0, min(p200 - 35, 40))
    b = max(0, min(ll - 40, 20))
    c = max(0, min(p200 - 15, 40))
    d = max(0, min(ip - 10, 20))
    ig = int(round(a * (0.2 + 0.005 * b) + 0.01 * c * d))
    
    if p200 <= 35:
        if p200 <= 15 and p40 <= 30 and p10 <= 50: res = "A-1-a (0)"
        elif p200 <= 25 and p40 <= 50: res = "A-1-b (0)"
        elif p200 <= 10 and p40 <= 51: res = "A-3 (0)"
        elif ll <= 40: res = f"A-2-4 (0)" if ip <= 10 else f"A-2-6 (0)"
        else: res = f"A-2-5 (0)" if ip <= 10 else f"A-2-7 (0)"
    else:
        if ll <= 40: grupo = "A-4" if ip <= 10 else "A-6"
        else: grupo = "A-7-5" if ip <= (ll - 30) else "A-7-6"
        res = f"{grupo} ({ig})"
    return f"AASHTO: {res} – (M 145)"

def classificar_sucs(p200, ll, ip, pedregulho, areia):
    if p200 < 50:
        prefixo = "G" if pedregulho > areia else "S"
        if p200 < 5: sufixo = "W" if (ll < 30) else "P" # Simplificado s/ Cu Cc
        elif p200 > 12: sufixo = "C" if ip > 7 and ip >= (0.73*(ll-20)) else "M"
        else: sufixo = "M-C"
        desc = "Pedregulho" if prefixo == "G" else "Areia"
        ligante = "argilosa" if "C" in sufixo else "siltosa"
        return f"SUCS: {prefixo}{sufixo} – {desc} {ligante} (ASTM D2487)"
    else:
        tipo = "C" if ip > 7 and ip >= (0.73*(ll-20)) else "M"
        comp = "L" if ll < 50 else "H"
        nome = "Argila" if tipo == "C" else "Silte"
        return f"SUCS: {tipo}{comp} – {nome} de {'baixa' if comp=='L' else 'alta'} plasticidade"

def classificar_mct(c_p, d_p):
    if c_p < 0.60: res, nome = "LG'", "Argila Laterítica"
    elif c_p < 1.10: res, nome = "LY'", "Limo Laterítico"
    elif c_p < 1.50: res, nome = "LA'", "Areia Argilosa Laterítica"
    else: res, nome = "AQ", "Areia Quartzosa"
    status = "Laterítico" if d_p > 1.5 else "Não Laterítico"
    return f"MCT: {res} – {nome} {status}"

# --- INTERFACE ---

st.title("🔬 Caracterização Geotécnica de Solos")
st.caption("Conforme NBR 7181, ASTM D2487, AASHTO M 145 e Classificação MCT")

col1, col2 = st.columns([1, 1.6])

with col1:
    st.subheader("📥 Entrada de Dados")
    
    with st.expander("Identificação e Índices", expanded=True):
        ll = st.number_input("Limite de Liquidez - LL (%)", value=35.0)
        lp = st.number_input("Limite de Plasticidade - LP (%)", value=20.0)
        ip = ll - lp
        st.write(f"IP: **{ip:.1f}%**")

    with st.expander("MCT (Ensaios Mini-MCV)", expanded=False):
        c_p = st.number_input("Coeficiente c'", value=1.20)
        d_p = st.number_input("Coeficiente d'", value=2.00)

    with st.expander("Peneiramento (NBR 7181)", expanded=True):
        peso_total = st.number_input("Massa Total Seca (g)", value=1000.0, help="Massa inicial antes da lavagem")
        df_base = pd.DataFrame({
            'Abertura (mm)': [50.8, 25.4, 9.5, 4.75, 2.0, 0.42, 0.075],
            'Peso Retido (g)': [0.0, 0.0, 50.0, 100.0, 200.0, 350.0, 150.0]
        })
        df_edit = st.data_editor(df_base, num_rows="dynamic")
        soma_retida = df_edit['Peso Retido (g)'].sum()
        st.write(f"Soma das frações: **{soma_retida:.1f}g**")
        if soma_retida > peso_total:
            st.warning("⚠️ Soma das peneiras maior que o peso total!")

with col2:
    if st.button("🚀 PROCESSAR ENSAIO", use_container_width=True):
        # Cálculos
        df_edit['% Retida Acum.'] = (df_edit['Peso Retido (g)'].cumsum() / peso_total) * 100
        df_edit['% Passante'] = 100 - df_edit['% Retida Acum.']
        
        # Gráfico
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.plot(df_edit['Abertura (mm)'], df_edit['% Passante'], 's-', color='#2c3e50', lw=2)
        ax.set_xscale('log')
        ax.set_xlabel('Diâmetro das Partículas (mm)')
        ax.set_ylabel('% Passante Acumulada')
        ax.invert_xaxis()
        ax.grid(True, which="both", alpha=0.3)
        st.pyplot(fig)

        # Classificações
        def get_p(m): 
            try: return df_edit[df_edit['Abertura (mm)'] <= m]['% Passante'].iloc[0]
            except: return 0
            
        p200, p40, p10 = get_p(0.075), get_p(0.42), get_p(2.0)
        pedregulho = 100 - get_p(4.75)
        areia = get_p(4.75) - p200
        
        c_sucs = classificar_sucs(p200, ll, ip, pedregulho, areia)
        c_aashto = classificar_aashto(p10, p40, p200, ll, ip)
        c_mct = classificar_mct(c_p, d_p)
        
        # Exibição
        st.subheader("🏁 Classificações Oficiais")
        st.success(f"**{c_sucs}**")
        st.info(f"**{c_aashto}**")
        st.warning(f"**{c_mct}**")
        
        # Memória de Cálculo (O "🧠 Critério Aplicado")
        m_sucs, m_aashto, m_mct = obter_criterios(p200, ll, ip, pedregulho, areia, p10, p40, c_p, d_p)
        
        with st.container():
            st.markdown("### 🧠 Critério Aplicado (Memória de Cálculo)")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.caption("**Lógica SUCS**")
                st.write(m_sucs)
            with col_b:
                st.caption("**Lógica AASHTO**")
                st.write(m_aashto)
            with col_c:
                st.caption("**Lógica MCT**")
                st.write(m_mct)

        # PDF
        # (Função gerar_pdf aqui seguindo a lógica de converter para bytes() como feito antes)
