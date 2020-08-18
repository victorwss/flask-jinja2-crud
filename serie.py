from flask import Flask, make_response, request, render_template, redirect, send_from_directory
from contextlib import closing
import sqlite3
import os
import werkzeug

# Observação: O código abaixo não contém uma estrutura dividida em camadas com blueprints, services, controllers, DAOs, models, etc., pois a ideia é tentar manter tudo bem simples.
#             Quando você estiver trabalhando em seu projeto real, tente separar isso tudo.
#             E idealmente num projeto grande, você teria um serviço fornecendo dados em formato JSON e alguma outra coisa utilizando-os para gerar o HTML, mas aqui está tudo numa coisa só.

############################
#### Definições da API. ####
############################

# Cria o objeto principal do Flask.
app = Flask(__name__)

# Quase todos os métodos terão estas três linhas para se certificar de que o login é válido. Se não for, o usuário será redirecionado para a tela de login.
#   logado = autenticar_login()
#   if logado is None:
#       return redirect("/")
#
# Esse código é bastante repetitivo, o que é bem chato. Até é possível resolver isso movendo-o para method decorators e/ou filtros, no entanto, para não complicarmos demais, vamos deixá-lo assim.

# Os métodos desta camada tem que ser idealmente um tanto "burros". Eles APENAS devem fazer o seguinte e nada mais:
# 1. Autenticação.
# 2. Retirar os dados relevantes da requisição.
# 3. Chamar alguma função no banco de dados ou na regra de negócio que faz o trabalho pesado.
# 4. Montar uma resposta à requisição.

# É importante notar-se que não devem haver regras de negócio aqui.
# Todo o trabalho que essas funções executam deve ser APENAS o de ler a requisição e escrever a resposta, delegando o trabalho de processamento às regras de negócio.

### Partes de login. ###

@app.route("/")
@app.route("/login")
def menu():
    # Autenticação.
    logado = autenticar_login()
    if logado is None:
        return render_template("/login.html", erro = "")

    # Monta a resposta.
    return render_template("menu.html", logado = logado, mensagem = "")

@app.route("/login", methods = ["POST"])
def login():
    # Extrai os dados do formulário.
    f = request.form
    if "login" not in f or "senha" not in f:
        return ":(", 422
    login = f["login"]
    senha = f["senha"]

    # Faz o processamento.
    logado = db_fazer_login(login, senha)

    # Monta a resposta.
    if logado is None:
        return render_template("login.html", erro = "Ops. A senha estava errada.")
    resposta = make_response(redirect("/"))

    # Armazena o login realizado com sucesso em cookies (autenticação).
    resposta.set_cookie("login", login, samesite = "Strict")
    resposta.set_cookie("senha", senha, samesite = "Strict")
    return resposta

@app.route("/logout", methods = ["POST"])
def logout():
    # Monta a resposta.
    resposta = make_response(render_template("login.html", mensagem = "Tchau."))

    # Limpa os cookies com os dados de login (autenticação).
    resposta.set_cookie("login", "", samesite = "Strict")
    resposta.set_cookie("senha", "", samesite = "Strict")
    return resposta

### Cadastro de séries. ###

# Tela de listagem de séries.
@app.route("/serie")
def listar_series_api():
    # Autenticação.
    logado = autenticar_login()
    if logado is None:
        return redirect("/")

    # Faz o processamento.
    lista = db_listar_series()

    # Monta a resposta.
    return render_template("lista_series.html", logado = logado, series = lista)

# Tela com o formulário de criação de séries.
@app.route("/serie/novo", methods = ["GET"])
def form_criar_serie_api():
    # Autenticação.
    logado = autenticar_login()
    if logado is None:
        return redirect("/")

    # Monta a resposta.
    return render_template("form_serie.html", logado = logado)

# Processa o formulário de criação de séries.
@app.route("/serie/novo", methods = ["POST"])
def criar_serie_api():
    # Autenticação.
    logado = autenticar_login()
    if logado is None:
        return redirect("/")

    # Extrai os dados do formulário.
    numero = request.form["numero"]
    turma = request.form["turma"]

    # Faz o processamento.
    ja_existia, serie = criar_serie(numero, turma)

    # Monta a resposta.
    mensagem = f"A série {numero}{turma} já existia com o id {serie['id_serie']}." if ja_existia else f"A série {numero}{turma} foi criada com id {serie['id_serie']}."
    return render_template("menu.html", logado = logado, mensagem = mensagem)

### Cadastro de alunos. ###

# Tela de listagem de alunos.
@app.route("/aluno")
def listar_alunos_api():
    # Autenticação.
    logado = autenticar_login()
    if logado is None:
        return redirect("/")

    # Faz o processamento.
    lista = db_listar_alunos()

    # Monta a resposta.
    return render_template("lista_alunos.html", logado = logado, alunos = lista)

# Tela com o formulário de criação de um novo aluno.
@app.route("/aluno/novo", methods = ["GET"])
def form_criar_aluno_api():
    # Autenticação.
    logado = autenticar_login()
    if logado is None:
        return redirect("/")

    # Faz o processamento.
    lista = db_listar_series_ordem()
    aluno = {'id_aluno': 'novo', 'nome': '', 'sexo': '', 'id_serie': '', 'id_foto': ''}

    # Monta a resposta.
    return render_template("form_aluno.html", logado = logado, aluno = aluno, series = lista)

# Tela com o formulário de alteração de um aluno existente.
@app.route("/aluno/<int:id_aluno>", methods = ["GET"])
def form_alterar_aluno_api(id_aluno):
    # Autenticação.
    logado = autenticar_login()
    if logado is None:
        return redirect("/")

    # Faz o processamento.
    aluno = db_consultar_aluno(id_aluno)
    series = db_listar_series_ordem()

    # Monta a resposta.
    if aluno is None:
        return render_template("menu.html", logado = logado, mensagem = f"Esse aluno não existe."), 404
    return render_template("form_aluno.html", logado = logado, aluno = aluno, series = series)

# Processa o formulário de criação de alunos. Inclui upload de fotos.
@app.route("/aluno/novo", methods = ["POST"])
def criar_aluno_api():
    # Autenticação.
    logado = autenticar_login()
    if logado is None:
        return redirect("/")

    # Extrai os dados do formulário.
    nome = request.form["nome"]
    sexo = request.form["sexo"]
    id_serie = request.form["id_serie"]

    # Faz o processamento.
    aluno = criar_aluno(nome, sexo, id_serie, salvar_arquivo_upload)

    # Monta a resposta.
    mensagem = f"O aluno {nome} foi criado com o id {aluno['id_aluno']}." if sexo == "M" else f"A aluna {nome} foi criada com o id {aluno['id_aluno']}."
    return render_template("menu.html", logado = logado, mensagem = mensagem)

# Processa o formulário de alteração de alunos. Inclui upload de fotos.
@app.route("/aluno/<int:id_aluno>", methods = ["POST"])
def editar_aluno_api(id_aluno):
    # Autenticação.
    logado = autenticar_login()
    if logado is None:
        return redirect("/")

    # Extrai os dados do formulário.
    nome = request.form["nome"]
    sexo = request.form["sexo"]
    id_serie = request.form["id_serie"]

    # Faz o processamento.
    status, aluno = editar_aluno(id_aluno, nome, sexo, id_serie, salvar_arquivo_upload, deletar_foto)

    # Monta a resposta.
    if status == 'não existe':
        mensagem = "Esse aluno nem mesmo existia mais." if sexo == "M" else "Essa aluna nem mesmo existia mais."
        return render_template("menu.html", logado = logado, mensagem = mensagem), 404
    mensagem = f"O aluno {nome} com o id {id_aluno} foi editado." if sexo == "M" else f"A aluna {nome} com o id {id_aluno} foi editada."
    return render_template("menu.html", logado = logado, mensagem = mensagem)

# Processa o botão de excluir um aluno.
@app.route("/aluno/<int:id_aluno>", methods = ["DELETE"])
def deletar_aluno_api(id_aluno):
    # Autenticação.
    logado = autenticar_login()
    if logado is None:
        return redirect("/")

    # Faz o processamento.
    aluno = apagar_aluno(id_aluno)

    # Monta a resposta.
    if aluno is None:
        return render_template("menu.html", logado = logado, mensagem = "Esse aluno nem mesmo existia mais."), 404
    mensagem = f"O aluno com o id {id_aluno} foi excluído." if aluno['sexo'] == "M" else f"A aluna com o id {id_aluno} foi excluída."
    return render_template("menu.html", logado = logado, mensagem = mensagem)

### Fotos dos alunos. ###

# Faz o download de uma foto.
@app.route("/aluno/foto/<id_foto>")
def aluno_download_foto(id_foto):
    # Autenticação.
    logado = autenticar_login()
    if logado is None:
        return redirect("/")

    # Monta a resposta.
    try:
        return send_from_directory("alunos_fotos", id_foto)
    except werkzeug.exceptions.NotFound as x:
        return send_from_directory("static", "no-photo.png")

# Deleta uma foto.
@app.route("/aluno/foto/<id_foto>", methods = ["DELETE"])
def aluno_deletar_foto(id_foto):
    # Autenticação.
    logado = autenticar_login()
    if logado is None:
        return redirect("/")

    # Faz o processamento.
    deletar_foto(id_foto)

    # Monta a resposta.
    return ""

###############################################
#### Coisas internas da controller da API. ####
###############################################

def extensao_arquivo(filename):
    if '.' not in filename: return ''
    return filename.rsplit('.', 1)[1].lower()

def salvar_arquivo_upload():
    import uuid
    if "foto" in request.files:
        foto = request.files["foto"]
        e = extensao_arquivo(foto.filename)
        if e in ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp']:
            u = uuid.uuid1()
            n = f"{u}.{e}"
            foto.save(os.path.join("alunos_fotos", n))
            return n
    return ""

def deletar_foto(id_foto):
    if id_foto == '': return
    p = os.path.join("alunos_fotos", id_foto)
    if os.path.exists(p):
        os.remove(p)

def autenticar_login():
    login = request.cookies.get("login", "")
    senha = request.cookies.get("senha", "")
    return db_fazer_login(login, senha)

##########################################
#### Definições de regras de negócio. ####
##########################################

def criar_serie(numero, turma):
    serie_ja_existe = db_verificar_serie(numero, turma)
    if serie_ja_existe is not None: return True, serie_ja_existe
    serie_nova = db_criar_serie(numero, turma)
    return False, serie_nova

def criar_aluno(nome, sexo, id_serie, salvar_foto):
    return db_criar_aluno(nome, sexo, id_serie, salvar_foto())

def editar_aluno(id_aluno, nome, sexo, id_serie, salvar_foto, apagar_foto):
    aluno = db_consultar_aluno(id_aluno)
    if aluno is None:
        return 'não existe', None
    id_foto = salvar_foto()
    if id_foto == "":
        id_foto = aluno["id_foto"]
    else:
        apagar_foto(aluno["id_foto"])
    db_editar_aluno(id_aluno, nome, sexo, id_serie, id_foto)
    return 'alterado', aluno

def apagar_aluno(id_aluno):
    aluno = db_consultar_aluno(id_aluno)
    if aluno is not None: db_deletar_aluno(id_aluno)
    return aluno

###############################################
#### Funções auxiliares de banco de dados. ####
###############################################

# Converte uma linha em um dicionário.
def row_to_dict(description, row):
    if row is None: return None
    d = {}
    for i in range(0, len(row)):
        d[description[i][0]] = row[i]
    return d

# Converte uma lista de linhas em um lista de dicionários.
def rows_to_dict(description, rows):
    result = []
    for row in rows:
        result.append(row_to_dict(description, row))
    return result

####################################
#### Definições básicas de DAO. ####
####################################

sql_create = """
CREATE TABLE IF NOT EXISTS serie (
    id_serie INTEGER PRIMARY KEY AUTOINCREMENT,
    numero INTEGER NOT NULL,
    turma VARCHAR(1) NOT NULL,
    UNIQUE(numero, turma)
);

CREATE TABLE IF NOT EXISTS aluno (
    id_aluno INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(50) NOT NULL,
    sexo VARCHAR(1) NOT NULL,
    id_serie INTEGER NOT NULL,
    id_foto VARCHAR(50) NOT NULL,
    FOREIGN KEY(id_serie) REFERENCES serie(id_serie)
);

CREATE TABLE IF NOT EXISTS usuario (
    login VARCHAR(50) PRIMARY KEY NOT NULL,
    senha VARCHAR(50) NOT NULL,
    nome VARCHAR(50) NOT NULL,
    FOREIGN KEY(login) REFERENCES serie(login)
);

REPLACE INTO usuario (login, senha, nome) VALUES ('ironman', 'ferro', 'Tony Stark');
REPLACE INTO usuario (login, senha, nome) VALUES ('spiderman', 'aranha', 'Peter Park');
REPLACE INTO usuario (login, senha, nome) VALUES ('batman', 'morcego', 'Bruce Wayne');
"""

# Observação: A tabela "usuario" acima não utiliza uma forma segura de se armazenar senhas. Isso será abordado mais para frente!

# Observação: Os métodos do DAO devem ser "burros". Eles apenas executam alguma instrução no banco de dados e nada mais.
#             Não devem ter inteligência, pois qualquer tipo de inteligência provavelmente trata-se de uma regra de negócio, e que portanto não deve ficar no DAO.

def conectar():
    return sqlite3.connect('serie.db')

def db_inicializar():
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.executescript(sql_create)
        con.commit()

def db_listar_series():
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("SELECT id_serie, numero, turma FROM serie")
        return rows_to_dict(cur.description, cur.fetchall())

def db_listar_series_ordem():
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("SELECT id_serie, numero, turma FROM serie ORDER BY numero, turma")
        return rows_to_dict(cur.description, cur.fetchall())

def db_verificar_serie(numero, turma):
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("SELECT id_serie, numero, turma FROM serie WHERE numero = ? AND turma = ?", [numero, turma])
        return row_to_dict(cur.description, cur.fetchone())

def db_consultar_aluno(id_aluno):
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("SELECT a.id_aluno, a.nome, a.sexo, a.id_serie, a.id_foto, s.numero, s.turma FROM aluno a INNER JOIN serie s ON a.id_serie = s.id_serie WHERE a.id_aluno = ?", [id_aluno])
        return row_to_dict(cur.description, cur.fetchone())

def db_listar_alunos():
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("SELECT a.id_aluno, a.nome, a.sexo, a.id_serie, a.id_foto, s.numero, s.turma FROM aluno a INNER JOIN serie s ON a.id_serie = s.id_serie")
        return rows_to_dict(cur.description, cur.fetchall())

def db_criar_serie(numero, turma):
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("INSERT INTO serie (numero, turma) VALUES (?, ?)", [numero, turma])
        id_serie = cur.lastrowid
        con.commit()
        return {'id_serie': id_serie, 'numero': numero, 'turma': turma}

def db_criar_aluno(nome, sexo, id_serie, id_foto):
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("INSERT INTO aluno (nome, sexo, id_serie, id_foto) VALUES (?, ?, ?, ?)", [nome, sexo, id_serie, id_foto])
        id_aluno = cur.lastrowid
        con.commit()
        return {'id_aluno': id_aluno, 'nome': nome, 'sexo': sexo, 'id_serie': id_serie, 'id_foto': id_foto}

def db_editar_aluno(id_aluno, nome, sexo, id_serie, id_foto):
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("UPDATE aluno SET nome = ?, sexo = ?, id_serie = ?, id_foto = ? WHERE id_aluno = ?", [nome, sexo, id_serie, id_foto, id_aluno])
        con.commit()
        return {'id_aluno': id_aluno, 'nome': nome, 'sexo': sexo, 'id_serie': id_serie, 'id_foto': id_foto}

def db_deletar_aluno(id_aluno):
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("DELETE FROM aluno WHERE id_aluno = ?", [id_aluno])
        con.commit()

def db_fazer_login(login, senha):
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("SELECT u.login, u.senha, u.nome FROM usuario u WHERE u.login = ? AND u.senha = ?", [login, senha])
        return row_to_dict(cur.description, cur.fetchone())

########################
#### Inicialização. ####
########################

if __name__ == "__main__":
    db_inicializar()
    app.run()