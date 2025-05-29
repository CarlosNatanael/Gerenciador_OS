from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

def criar_banco():
    conn = sqlite3.connect("os.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            equipamento TEXT NOT NULL,
            problema TEXT NOT NULL,
            solucao TEXT NOT NULL,
            tempo_reparo REAL,
            inicio_os TEXT,
            fim_os TEXT
        )
    ''')
    conn.commit()
    conn.close()

criar_banco()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/nova", methods=["GET", "POST"])
def nova_os():
    if request.method == "POST":
        data = request.form["data"]
        equipamento = request.form["equipamento"]
        problema = request.form["problema"]
        solucao = request.form["solucao"]
        inicio = datetime.strptime(request.form["inicio"], "%Y-%m-%dT%H:%M")
        fim = datetime.strptime(request.form["fim"], "%Y-%m-%dT%H:%M")
        tempo_reparo = (fim - inicio).total_seconds() / 60

        conn = sqlite3.connect("os.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ordens_servico (data, equipamento, problema, solucao, tempo_reparo, inicio_os, fim_os)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (data, equipamento, problema, solucao, tempo_reparo,
              inicio.strftime("%d/%m/%Y %H:%M"), fim.strftime("%d/%m/%Y %H:%M")))
        conn.commit()
        conn.close()
        return redirect("/historico")
    return render_template("nova_os.html")

@app.route("/historico")
def historico():
    conn = sqlite3.connect("os.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ordens_servico ORDER BY data DESC")
    os_list = cursor.fetchall()
    conn.close()
    return render_template("historico.html", os_list=os_list)

if __name__ == "__main__":
    app.run(debug=True)
