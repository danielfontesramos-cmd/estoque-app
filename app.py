import configparser
from flask import Flask, render_template, request
import mysql.connector

app = Flask(__name__)

config = configparser.ConfigParser()
config.read("config.ini", encoding="utf-8")

db = config["database"]

def conectar_banco():
    return mysql.connector.connect(
        host=db["host"],
        port=db.getint("port"),
        user=db["user"],
        password=db["password"],
        database=db["database"]
    )

@app.route("/")
def inicio():
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)
        
        # Buscar todas as sessões para o dropdown
        cursor.execute("SELECT id, nome FROM secoes ORDER BY nome")
        secoes = cursor.fetchall()
        
        # Buscar todos os fabricantes para o dropdown
        cursor.execute("SELECT id, nome FROM fabricantes ORDER BY nome")
        fabricantes = cursor.fetchall()
        
        cursor.close()
        conexao.close()
        
        return render_template("index.html", secoes=secoes, fabricantes=fabricantes)
    except Exception as erro:
        return f"""
        <h1>Programa de Estoque</h1>
        <p>Erro ao conectar no banco:</p>
        <pre>{erro}</pre>
        """, 500

@app.route("/buscar_codigo", methods=["POST"])
def buscar_codigo():
    try:
        codigo = request.form.get("codigo_barras")
        
        if not codigo:
            return render_template("resultado.html", erro="Digite um código de barras")
        
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)
        
        # Buscar produto pelo código de barras
        cursor.execute("""
            SELECT 
                p.*,
                f.nome as nome_fabricante,
                s.nome as nome_secao
            FROM produtos p
            LEFT JOIN fabricantes f ON p.fabricante_id = f.id
            LEFT JOIN secoes s ON p.secao_id = s.id
            WHERE p.codigo_barras = %s
        """, (codigo,))
        
        produto = cursor.fetchone()
        
        cursor.close()
        conexao.close()
        
        if not produto:
            return render_template("resultado.html", erro=f"Produto com código {codigo} não encontrado")
        
        # Calcular total
        total = 0
        if produto["qtd_deposito_central"]: total += produto["qtd_deposito_central"]
        if produto["qtd_deposito_secundario"]: total += produto["qtd_deposito_secundario"]
        if produto["qtd_loja_palmeiras"]: total += produto["qtd_loja_palmeiras"]
        if produto["qtd_loja_cidade"]: total += produto["qtd_loja_cidade"]
        
        produto["total_estoque"] = total
        
        return render_template("detalhes.html", produto=produto)
        
    except Exception as erro:
        return render_template("resultado.html", erro=f"Erro na busca: {str(erro)}")

@app.route("/buscar_nome", methods=["POST"])
def buscar_nome():
    try:
        nome = request.form.get("nome_produto")
        
        if not nome:
            return render_template("resultado.html", erro="Digite um nome para buscar")
        
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)
        
        # Buscar produtos pelo nome (busca parcial)
        cursor.execute("""
            SELECT 
                p.*,
                f.nome as nome_fabricante,
                s.nome as nome_secao
            FROM produtos p
            LEFT JOIN fabricantes f ON p.fabricante_id = f.id
            LEFT JOIN secoes s ON p.secao_id = s.id
            WHERE p.nome LIKE %s
            ORDER BY p.nome
        """, (f"%{nome}%",))
        
        produtos = cursor.fetchall()
        
        cursor.close()
        conexao.close()
        
        if not produtos:
            return render_template("resultado.html", erro=f"Nenhum produto encontrado com nome contendo '{nome}'")
        
        # Calcular total para cada produto
        for produto in produtos:
            total = 0
            if produto["qtd_deposito_central"]: total += produto["qtd_deposito_central"]
            if produto["qtd_deposito_secundario"]: total += produto["qtd_deposito_secundario"]
            if produto["qtd_loja_palmeiras"]: total += produto["qtd_loja_palmeiras"]
            if produto["qtd_loja_cidade"]: total += produto["qtd_loja_cidade"]
            produto["total_estoque"] = total
        
        return render_template("lista.html", produtos=produtos, busca=f"Busca por nome: '{nome}'")
        
    except Exception as erro:
        return render_template("resultado.html", erro=f"Erro na busca: {str(erro)}")

@app.route("/detalhes/<codigo_barras>")
def detalhes_produto(codigo_barras):
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)
        
        # Buscar produto pelo código de barras
        cursor.execute("""
            SELECT 
                p.*,
                f.nome as nome_fabricante,
                s.nome as nome_secao
            FROM produtos p
            LEFT JOIN fabricantes f ON p.fabricante_id = f.id
            LEFT JOIN secoes s ON p.secao_id = s.id
            WHERE p.codigo_barras = %s
        """, (codigo_barras,))
        
        produto = cursor.fetchone()
        
        cursor.close()
        conexao.close()
        
        if not produto:
            return render_template("resultado.html", erro=f"Produto com código {codigo_barras} não encontrado")
        
        # Calcular total
        total = 0
        if produto["qtd_deposito_central"]: total += produto["qtd_deposito_central"]
        if produto["qtd_deposito_secundario"]: total += produto["qtd_deposito_secundario"]
        if produto["qtd_loja_palmeiras"]: total += produto["qtd_loja_palmeiras"]
        if produto["qtd_loja_cidade"]: total += produto["qtd_loja_cidade"]
        
        produto["total_estoque"] = total
        
        return render_template("detalhes.html", produto=produto)
        
    except Exception as erro:
        return render_template("resultado.html", erro=f"Erro ao buscar detalhes: {str(erro)}")

@app.route("/filtrar_unidade", methods=["POST"])
def filtrar_unidade():
    try:
        unidade = request.form.get("unidade")
        
        if not unidade:
            return render_template("resultado.html", erro="Selecione uma unidade")
        
        # Mapear unidade para coluna no banco
        colunas_unidades = {
            "Loja Palmeiras": "qtd_loja_palmeiras",
            "Loja Cidade": "qtd_loja_cidade",
            "Depósito Central": "qtd_deposito_central",
            "Depósito Secundário": "qtd_deposito_secundario"
        }
        
        if unidade not in colunas_unidades:
            return render_template("resultado.html", erro=f"Unidade '{unidade}' inválida")
        
        coluna = colunas_unidades[unidade]
        
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)
        
        # Buscar produtos com estoque na unidade selecionada
        cursor.execute(f"""
            SELECT 
                p.*,
                f.nome as nome_fabricante,
                s.nome as nome_secao
            FROM produtos p
            LEFT JOIN fabricantes f ON p.fabricante_id = f.id
            LEFT JOIN secoes s ON p.secao_id = s.id
            WHERE p.{coluna} > 0
            ORDER BY p.nome
        """)
        
        produtos = cursor.fetchall()
        
        cursor.close()
        conexao.close()
        
        if not produtos:
            return render_template("resultado.html", erro=f"Nenhum produto encontrado na {unidade}")
        
        # Calcular total para cada produto
        for produto in produtos:
            total = 0
            if produto["qtd_deposito_central"]: total += produto["qtd_deposito_central"]
            if produto["qtd_deposito_secundario"]: total += produto["qtd_deposito_secundario"]
            if produto["qtd_loja_palmeiras"]: total += produto["qtd_loja_palmeiras"]
            if produto["qtd_loja_cidade"]: total += produto["qtd_loja_cidade"]
            produto["total_estoque"] = total
        
        return render_template("lista.html", produtos=produtos, busca=f"Filtro por unidade: {unidade}")
        
    except Exception as erro:
        return render_template("resultado.html", erro=f"Erro no filtro: {str(erro)}")

@app.route("/filtrar_secao", methods=["POST"])
def filtrar_secao():
    try:
        secao_id = request.form.get("secao_id")
        
        if not secao_id:
            return render_template("resultado.html", erro="Selecione uma sessão")
        
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)
        
        # Buscar produtos da sessão selecionada
        cursor.execute("""
            SELECT 
                p.*,
                f.nome as nome_fabricante,
                s.nome as nome_secao
            FROM produtos p
            LEFT JOIN fabricantes f ON p.fabricante_id = f.id
            LEFT JOIN secoes s ON p.secao_id = s.id
            WHERE p.secao_id = %s
            ORDER BY p.nome
        """, (secao_id,))
        
        produtos = cursor.fetchall()
        
        # Buscar nome da sessão
        cursor.execute("SELECT nome FROM secoes WHERE id = %s", (secao_id,))
        secao = cursor.fetchone()
        
        cursor.close()
        conexao.close()
        
        if not produtos:
            return render_template("resultado.html", erro=f"Nenhum produto encontrado na sessão selecionada")
        
        # Calcular total para cada produto
        for produto in produtos:
            total = 0
            if produto["qtd_deposito_central"]: total += produto["qtd_deposito_central"]
            if produto["qtd_deposito_secundario"]: total += produto["qtd_deposito_secundario"]
            if produto["qtd_loja_palmeiras"]: total += produto["qtd_loja_palmeiras"]
            if produto["qtd_loja_cidade"]: total += produto["qtd_loja_cidade"]
            produto["total_estoque"] = total
        
        return render_template("lista.html", produtos=produtos, busca=f"Filtro por sessão: {secao['nome'] if secao else 'Desconhecida'}")
        
    except Exception as erro:
        return render_template("resultado.html", erro=f"Erro no filtro: {str(erro)}")

@app.route("/filtrar_fabricante", methods=["POST"])
def filtrar_fabricante():
    try:
        fabricante_id = request.form.get("fabricante_id")
        
        if not fabricante_id:
            return render_template("resultado.html", erro="Selecione um fabricante")
        
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)
        
        # Buscar produtos do fabricante selecionado
        cursor.execute("""
            SELECT 
                p.*,
                f.nome as nome_fabricante,
                s.nome as nome_secao
            FROM produtos p
            LEFT JOIN fabricantes f ON p.fabricante_id = f.id
            LEFT JOIN secoes s ON p.secao_id = s.id
            WHERE p.fabricante_id = %s
            ORDER BY p.nome
        """, (fabricante_id,))
        
        produtos = cursor.fetchall()
        
        # Buscar nome do fabricante
        cursor.execute("SELECT nome FROM fabricantes WHERE id = %s", (fabricante_id,))
        fabricante = cursor.fetchone()
        
        cursor.close()
        conexao.close()
        
        if not produtos:
            return render_template("resultado.html", erro=f"Nenhum produto encontrado do fabricante selecionado")
        
        # Calcular total para cada produto
        for produto in produtos:
            total = 0
            if produto["qtd_deposito_central"]: total += produto["qtd_deposito_central"]
            if produto["qtd_deposito_secundario"]: total += produto["qtd_deposito_secundario"]
            if produto["qtd_loja_palmeiras"]: total += produto["qtd_loja_palmeiras"]
            if produto["qtd_loja_cidade"]: total += produto["qtd_loja_cidade"]
            produto["total_estoque"] = total
        
        return render_template("lista.html", produtos=produtos, busca=f"Filtro por fabricante: {fabricante['nome'] if fabricante else 'Desconhecido'}")
        
    except Exception as erro:
        return render_template("resultado.html", erro=f"Erro no filtro: {str(erro)}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)