import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF
from scipy.interpolate import interp1d
import io

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Geotecnia Pro - Normativo v3.5", layout="wide")

# =====================================================================
#  DICIONÁRIOS DE INTERPRETAÇÃO TÉCNICA (ACRESCENTADOS)
# =====================================================================
INTERP_SUCS = {
    "GW": "Pedregulho bem graduado: Excelente para base de pavimentos e fundações.",
    "GP": "Pedregulho mal graduado: Boa capacidade de carga, requer compactação controlada.",
    "GM": "Pedregulho siltoso: Estável, sensível à umidade.",
    "GC": "Pedregulho argiloso: Boa coesão, útil para barragens e núcleos.",
    "SW": "Areia bem graduada: Excelente para drenagem e aterros estruturais.",
    "SP": "Areia mal graduada: Bom para aterros, pode apresentar instabilidade lateral.",
    "SM": "Areia siltosa: Comportamento intermediário, risco de erosão interna.",
    "SC": "Areia argilosa: Material granular com finos coesivos, boa estabilidade.",
    "CL": "Argila de baixa plasticidade: Solo firme, sujeito a assentamentos lentos.",
    "ML": "Silte de baixa plasticidade: Instável na presença de água, risco de liquefação.",
    "CH": "Argila de alta plasticidade: Muito compressível, grandes variações de volume.",
    "MH": "Silte de alta plasticidade: Comportamento elástico, difícil compactação.",
    "CL-ML": "Solo de transição argila-silte: Comportamento ambíguo, atenção à drenagem."
}

def interpretar_ig(ig):
    """Interpretação do Índice de Grupo (AASHTO)"""
    if ig == 0:
        return "Excelente a Bom (Ideal para subleito rodoviário)."
    if 1 <= ig <= 4:
        return "Bom a Sofrível (Requer atenção à drenagem)."
    if 5 <= ig <= 9:
        return "Sofrível a Pobre (Pode requerer estabilização com cal/cimento)."
    return "Pobre a Mau (Material inadequado para camadas nobres sem tratamento)."

# =====================================================================
#  1. CÁLCULO DE DIÂMETROS (INTERPOLAÇÃO LOG-LINEAR)
# =====================================================================
def calcular_diametros_seguro(df):
    try:
        df_sorted = df.sort_values('Abertura (mm)')
        df_sorted = df_sorted[df_sorted['Abertura (mm)'] > 0]
        
        x = df_sorted['% Passante'].values
        y = df_sorted['Abertura (mm)'].values
        
        min_p, max_p = x.min(), x.max()
        
        def interp(pct):
            if pct < min_p or pct > max_p:
                return None
            f = interp1d(x, np.log10(y), kind='linear')
            return 10 ** f(pct)

        d10, d30, d60 = interp(10), interp(30), interp(60)
        
        cu = (d60 / d10) if (d10 and d60) else None
        cc = ((d30**2) / (d60 * d10)) if (d10 and d30 and d60) else None
        return d10, d30, d60, cu, cc
    except Exception:
        return None, None, None, None, None

# =====================================================================
#  2. SUCS REFINADO (ASTM D2487) - C-M REMOVIDO
# =====================================================================
def classificar_sucs_refinado(p200, p4, ll, ip, cu, cc):
    if ip < 0:
        ip = 0
    linha_a = 0.73 * (ll - 20)
    
    # SOLOS GROSSOS (< 50% passa na #200)
    if p200 < 50:
        pedregulho = 100 - p4
        areia = p4 - p200
        pref = "G" if pedregulho > areia else "S"
        
        if p200 < 5:
            if cu is None or cc is None:
                return f"{pref} (Dados Insuficientes)"
            if pref == "G":
                grad = "W" if (cu >= 4 and 1 <= cc <= 3) else "P"
            else:
                grad = "W" if (cu >= 6 and 1 <= cc <= 3) else "P"
            return f"{pref}{grad}"
            
        elif p200 > 12:
            suf = "C" if (ip > 7 and ip >= linha_a) else "M"
            return f"{pref}{suf}"
            
        else:  # 5% a 12%
            if cu is None or cc is None:
                return f"{pref}-DUPLA (Falta Cu/Cc)"
            if pref == "G":
                grad = "W" if (cu >= 4 and 1 <= cc <= 3) else "P"
            else:
                grad = "W" if (cu >= 6 and 1 <= cc <= 3) else "P"
            suf = "C" if (ip > 7 and ip >= linha_a) else "M"
            return f"{pref}{grad}-{pref}{suf}"

    # SOLOS FINOS (>= 50% passa na #200)
    else:
        if ll < 50:
            if ip > 7 and ip >= linha_a:
                return "CL"
            elif ip < 4 or ip < linha_a:
                return "ML"
            else:
                return "CL-ML"
        else:
            return "CH" if ip >= linha_a else "MH"

# =====================================================================
#  3. AASHTO M 145 - IP NEGATIVO TRATADO, A-3 EXIGE IP=0
# =====================================================================
def classificar_aashto_final(p10, p40, p200, ll, ip):
    ip_eff = max(0, ip)   # IP negativo → 0 (NP)
    
    grupo = "Indeterminado"
    if p200 <= 35:
        if p10 <= 50 and p40 <= 30 and p200 <= 15 and ip_eff <= 6:
            grupo = "A-1-a"
        elif p40 <= 50 and p200 <= 25 and ip_eff <= 6:
            grupo = "A-1-b"
        elif p40 >= 51 and p200 <= 10 and ip_eff == 0:
            grupo = "A-3"
        else:
            if ll <= 40:
                grupo = "A-2-4" if ip_eff <= 10 else "A-2-6"
            else:
                grupo = "A-2-5" if ip_eff <= 10 else "A-2-7"
    else:
        if ll <= 40:
            grupo = "A-4" if ip_eff <= 10 else "A-6"
        else:
            if ip_eff <= 10:
                grupo = "A-5"
            else:
                grupo = "A-7-5" if ip_eff <= (ll - 30) else "A-7-6"
    
    t1 = max(0, (p200 - 35) * (0.2 + 0.005 * (ll - 40)))
    t2 = max(0, 0.01 * (p200 - 15) * (ip_eff - 10))
    
    if grupo in ["A-1-a", "A-1-b", "A-3", "A-2-4", "A-2-5"]:
        ig = 0
    elif grupo in ["A-2-6", "A-2-7"]:
        ig = t2
    else:
        ig = t1 + t2
    
    return f"{grupo} ({int(round(ig))})", t1, t2

# =====================================================================
#  4. GERADOR DE PDF - COM DESCRIÇÕES (BUFFER DE BYTES)
# =====================================================================
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'RELATÓRIO GEOTÉCNICO', 0, 1, 'C')
        self.ln(5)

def gerar_pdf(d):
    pdf = PDFReport()
    pdf.add_page()
    
    # RESULTADOS
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. CLASSIFICAÇÃO", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, f"SUCS: {d['sucs']}", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, f"→ {d['sucs_desc']}", ln=True)
    pdf.ln(2)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, f"AASHTO: {d['aashto']}", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, f"→ {d['aashto_desc']}", ln=True)
    pdf.ln(2)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, f"MCT: {d['mct']}", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, "→ Classificação para solos tropicais. Valor inserido manualmente.", ln=True)
    
    # PARÂMETROS FÍSICOS
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. PARÂMETROS FÍSICOS", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(50, 8, f"Massa Seca: {d['massa']} g")
    pdf.cell(50, 8, f"LL: {d['ll']}%")
    pdf.cell(50, 8, f"LP: {d['lp']}%")
    pdf.cell(40, 8, f"IP: {d['ip']}%", ln=True)
    
    # GRANULOMETRIA
    pdf.ln(2)
    pdf.cell(0, 8, "3. PARÂMETROS GRANULOMÉTRICOS", ln=True)
    pdf.cell(60, 8, f"D10: {d['d10']}")
    pdf.cell(60, 8, f"D30: {d['d30']}")
    pdf.cell(60, 8, f"D60: {d['d60']}", ln=True)
    pdf.cell(60, 8, f"Cu: {d['cu']}")
    pdf.cell(60, 8, f"Cc: {d['cc']}", ln=True)
    
    buffer = io.BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()

# =====================================================================
#  INTERFACE PRINCIPAL
# =====================================================================
st.title("🔬 Geotecnia Pro - DashBoard Normativo")
st.markdown("---")

col_in, col_out = st.columns([1, 1.5])

with col_in:
    st.subheader("📥 Dados de Laboratório")
    
    # Massa e Limites
    m_seca = st.number_input("Massa Seca Total (g)", value=1000.0)
    c_ll, c_lp = st.columns(2)
    ll = c_ll.number_input("LL (%)", value=42.0)
    lp = c_lp.number_input("LP (%)", value=26.0)
    ip = ll - lp
    st.info(f"Índice de Plasticidade (IP): {ip:.1f}%")
    
    # --- CLASSIFICAÇÃO MCT (ENSAIOS MINI-MCV) ---
    st.markdown("**Classificação MCT (ensaios Mini-MCV)**")
    st.caption("Preencha os parâmetros obtidos em laboratório para cálculo automático.")
    
    col_c, col_d, col_p = st.columns(3)
    with col_c:
        c_lin = st.number_input("Coeficiente c'", value=0.0, step=0.1, format="%.2f",
                                help="Coeficiente linear da curva de deformabilidade Mini-MCV")
    with col_d:
        d_lin = st.number_input("Coeficiente d'", value=0.0, step=0.1, format="%.2f",
                                help="Coeficiente angular (inclinação) da curva Mini-MCV")
    with col_p:
        perda_massa = st.number_input("Perda por Imersão (%)", value=0.0, step=0.1, format="%.1f",
                                      help="Ensaio de perda de massa por imersão (NBR 13602)")
    
    def classificar_mct(c, d, perda):
        if c <= 0 or d <= 0:
            return "⏸️ Aguardando dados (c' e d' > 0)"
        
        if d > 20:  # Laterítico
            grupo = "LG'" if c >= 1.5 else "LA'"
        else:       # Não-laterítico
            grupo = "NG'" if c >= 0.6 else "NS'"
        
        if perda > 2.0:
            return f"{grupo} ⚠️ Perda {perda:.1f}%"
        else:
            return grupo
    
    mct_resultado = classificar_mct(c_lin, d_lin, perda_massa)
    st.caption("ℹ️ Este campo deve ser preencihido com os dados do laboratório.")
    
    # --- TABELA DE PENEIRAS (MELHORADA) ---
    st.subheader("📊 Análise Granulométrica")
    
    # DataFrame base com identificação das peneiras
    df_base = pd.DataFrame({
        'Peneira': ['2"', '3/4"', '#4', '#10', '#40', '#200'],
        'Abertura (mm)': [50.8, 19.1, 4.75, 2.0, 0.42, 0.075],
        'Peso Retido (g)': [0.0, 50.0, 100.0, 150.0, 400.0, 250.0]
    })
    
    # Expander para adicionar peneiras de finos (sedimentação) - OPCIONAL
    with st.expander("➕ Adicionar peneiras para fração fina (opcional)"):
        st.caption("Inclua dados de sedimentação (peneiras #270, #1000, etc.) para melhor representação gráfica.")
        incluir_finos = st.checkbox("Incluir peneiras finas")
        if incluir_finos:
            finos_df = pd.DataFrame({
                'Peneira': ['#270', '#1000', 'Sedim.'],
                'Abertura (mm)': [0.053, 0.025, 0.002],
                'Peso Retido (g)': [0.0, 0.0, 0.0]
            })
            df_base = pd.concat([df_base, finos_df], ignore_index=True)
    
    # Editor de dados
    df_edit = st.data_editor(
        df_base,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "Peneira": st.column_config.TextColumn("Peneira", width="small"),
            "Abertura (mm)": st.column_config.NumberColumn("Abertura (mm)", format="%.3f", width="small"),
            "Peso Retido (g)": st.column_config.NumberColumn("Peso Retido (g)", format="%.1f", width="medium")
        }
    )

with col_out:
    if st.button("🚀 PROCESSAR ANÁLISE", type="primary", use_container_width=True):
        # --- PRÉ-PROCESSAMENTO ---
        df_proc = df_edit[df_edit['Abertura (mm)'] > 0].copy()
        
        if df_proc.empty:
            st.error("Insira dados válidos de granulometria.")
        else:
            # Validação de peneiras críticas
            min_user_d = df_proc['Abertura (mm)'].min()
            max_user_d = df_proc['Abertura (mm)'].max()
            
            missing_sieves = []
            if max_user_d < 2.0:
                missing_sieves.append("#10 (2.0mm)")
            if max_user_d < 0.42 and min_user_d > 0.42:
                missing_sieves.append("#40 (0.42mm)")
            if min_user_d > 0.075:
                missing_sieves.append("#200 (0.075mm)")
            
            if missing_sieves:
                st.warning(
                    f"⚠️ **Atenção: Extrapolação Detectada!**\n\n"
                    f"A sua curva granulométrica não abrange as peneiras: {', '.join(missing_sieves)}.\n"
                    "O sistema assumirá 0% ou 100% para estes valores, o que pode distorcer a classificação. "
                    "Sugestão: Adicione peneiras para cobrir toda a faixa."
                )
            
            # Cálculo das porcentagens
            df_proc['% Passante'] = 100 - (df_proc['Peso Retido (g)'].cumsum() / m_seca * 100)
            df_proc['% Passante'] = df_proc['% Passante'].clip(0, 100)
            
            # Interpolação logarítmica para peneiras críticas
            def get_p_log(diametro_alvo):
                if diametro_alvo > df_proc['Abertura (mm)'].max():
                    return 100.0
                if diametro_alvo < df_proc['Abertura (mm)'].min():
                    return 0.0
                f_log = interp1d(np.log10(df_proc['Abertura (mm)']), df_proc['% Passante'], kind='linear')
                return float(f_log(np.log10(diametro_alvo)))
            
            p10 = get_p_log(2.0)
            p40 = get_p_log(0.42)
            p200 = get_p_log(0.075)
            p4 = get_p_log(4.75)
            
            d10, d30, d60, cu, cc = calcular_diametros_seguro(df_proc)
            
            # Classificações
            sucs = classificar_sucs_refinado(p200, p4, ll, ip, cu, cc)
            aashto, t1, t2 = classificar_aashto_final(p10, p40, p200, ll, ip)
            
            # --- GRÁFICO COM PONTO VIRTUAL EM 0.001 mm (CORREÇÃO VISUAL) ---
            df_plot = df_proc.copy()
            if p200 is not None and not np.isnan(p200):
                if 0.001 not in df_plot['Abertura (mm)'].values:
                    ponto_fino = pd.DataFrame({
                        'Abertura (mm)': [0.001],
                        'Peso Retido (g)': [0.0],
                        '% Passante': [p200]
                    })
                    df_plot = pd.concat([df_plot, ponto_fino], ignore_index=True)
                    df_plot = df_plot.sort_values('Abertura (mm)')
            
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.axvspan(0.001, 0.075, color='#e6f2ff', alpha=0.5, label='Finos (argila + silte)')
            ax.axvspan(0.075, 4.75, color='#fff9c4', alpha=0.5, label='Areia')
            ax.axvspan(4.75, 100, color='#ffe0b2', alpha=0.5, label='Pedregulho')
            ax.plot(df_plot['Abertura (mm)'], df_plot['% Passante'], 'o-', color='#1f77b4', linewidth=2, markersize=6)
            ax.set_xscale('log')
            ax.invert_xaxis()
            ax.set_xlim(100, 0.001)
            ax.set_ylim(0, 100)
            ax.set_xlabel('Diâmetro dos Grãos (mm)')
            ax.set_ylabel('Porcentagem que Passa (%)')
            ax.grid(True, which='both', alpha=0.3)
            ax.legend(loc='best')
            st.pyplot(fig)
            
            # --- MÉTRICAS COM INTERPRETAÇÃO ---
            st.subheader("🏁 Resultados e Interpretação")
            
            # Extrai o símbolo principal para SUCS (antes do hífen, se houver dupla)
            sucs_simbolo = sucs.split('-')[0].split()[0]  # Ex: "SW-SM" → "SW"
            sucs_desc = INTERP_SUCS.get(sucs_simbolo, "Solo com comportamento misto. Consulte norma.")
            
            # Extrai o IG da string AASHTO
            try:
                ig_val = int(aashto.split('(')[1].split(')')[0])
            except:
                ig_val = 0
            aashto_desc = interpretar_ig(ig_val)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("SUCS", sucs)
                st.caption(sucs_desc)
            with c2:
                st.metric("AASHTO", aashto)
                st.caption(aashto_desc)
            with c3:
                st.metric("MCT", mct_man)
                st.caption("Classificação tropical – inserida manualmente.")
            
            # --- BOTÃO PDF (COM DESCRIÇÕES) ---
            dados_pdf = {
                'sucs': sucs,
                'sucs_desc': sucs_desc,
                'aashto': aashto,
                'aashto_desc': aashto_desc,
                'mct': mct_man,
                'massa': m_seca,
                'll': ll,
                'lp': lp,
                'ip': ip,
                'd10': f"{d10:.3f}" if d10 else "-",
                'd30': f"{d30:.3f}" if d30 else "-",
                'd60': f"{d60:.3f}" if d60 else "-",
                'cu': f"{cu:.2f}" if cu else "-",
                'cc': f"{cc:.2f}" if cc else "-"
            }
            
            st.download_button(
                "📥 Baixar Relatório Técnico (PDF com descrições)",
                data=gerar_pdf(dados_pdf),
                file_name="relatorio_geotecnico.pdf",
                mime="application/pdf"
            )
