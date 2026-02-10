from flask import Flask, render_template, request, jsonify
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

def classificar_solos(ll, ip, passa_200):
    # Lógica simplificada SUCS
    if passa_200 < 50:
        sucs = "Solo Grosso"
    else:
        if ip > (0.73 * (ll - 20)): sucs = "CH/CL"
        else: sucs = "MH/ML"
    
    # Lógica simplificada AASHTO
    if passa_200 <= 35: aashto = "A-1 a A-3"
    else: aashto = "A-4 a A-7"
    
    return sucs, aashto

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calcular', methods=['POST'])
def calcular():
    dados = request.json
    # Aqui entraria a lógica de cálculo de % passante acumulada
    sucs, aashto = classificar_solos(float(dados['ll']), float(dados['ip']), float(dados['passa_200']))
    
    return jsonify({
        "sucs": sucs,
        "aashto": aashto,
        "mct": "Em desenvolvimento (Requer ensaio Mini-MCV)"
    })

if __name__ == '__main__':
    app.run(debug=True)
