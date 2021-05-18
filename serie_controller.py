from flask import Flask, make_response, request, render_template, redirect, send_from_directory
import serie_rn as rn
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

    # Obtém o login e senha do cookie.
    cred = ler_cookies_login()

    # Autenticação.
    try:
        logado = cred.fazer_login()
    except rn.NaoLogado:
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
    cred = rn.Credenciais(login, senha)

    # Faz o processamento.
    try:
        logado = cred.fazer_login()
    except rn.NaoLogado:
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

    # Obtém o login e senha do cookie.
    cred = ler_cookies_login()

    # Faz o processamento.
    try:
        lista, logado = rn.ModeloLMSAutenticado(cred).listar_series()
    except rn.NaoLogado:
        return redirect("/")

    # Monta a resposta.
    return render_template("lista_series.html", logado = logado, series = lista)

# Tela com o formulário de criação de séries.
@app.route("/serie/novo", methods = ["GET"])
def form_criar_serie_api():

    # Obtém o login e senha do cookie.
    cred = ler_cookies_login()

    # Faz o processamento.
    try:
        logado = cred.fazer_login()
    except rn.NaoLogado:
        return redirect("/")

    # Monta a resposta.
    return render_template("form_serie.html", logado = logado)

# Processa o formulário de criação de séries.
@app.route("/serie/novo", methods = ["POST"])
def criar_serie_api():

    # Extrai os dados do formulário.
    numero = request.form["numero"]
    turma = request.form["turma"]

    # Obtém o login e senha do cookie.
    cred = ler_cookies_login()

    # Faz o processamento.
    try:
        ja_existia, serie, logado = rn.ModeloLMSAutenticado(cred).criar_serie(numero, turma)
    except rn.NaoLogado:
        return redirect("/")

    # Monta a resposta.
    mensagem = f"A série {numero}{turma} já existia com o id {serie['id_serie']}." if ja_existia else f"A série {numero}{turma} foi criada com id {serie['id_serie']}."
    return render_template("menu.html", logado = logado, mensagem = mensagem)

### Cadastro de alunos. ###

# Tela de listagem de alunos.
@app.route("/aluno")
def listar_alunos_api():

    # Obtém o login e senha do cookie.
    cred = ler_cookies_login()

    # Faz o processamento.
    try:
        lista, logado = rn.ModeloLMSAutenticado(cred).listar_alunos()
    except rn.NaoLogado:
        return redirect("/")

    # Monta a resposta.
    return render_template("lista_alunos.html", logado = logado, alunos = lista)

# Tela com o formulário de criação de um novo aluno.
@app.route("/aluno/novo", methods = ["GET"])
def form_criar_aluno_api():

    # Obtém o login e senha do cookie.
    cred = ler_cookies_login()

    # Faz o processamento com autenticação.
    try:
        lista, logado = rn.ModeloLMSAutenticado(cred).listar_series_ordem()
    except rn.NaoLogado:
        return redirect("/")

    # Monta a resposta.
    aluno = {'id_aluno': 'novo', 'nome': '', 'sexo': '', 'id_serie': '', 'id_foto': ''}
    return render_template("form_aluno.html", logado = logado, aluno = aluno, series = lista)

# Tela com o formulário de alteração de um aluno existente.
@app.route("/aluno/<int:id_aluno>", methods = ["GET"])
def form_alterar_aluno_api(id_aluno):

    # Obtém o login e senha do cookie.
    cred = ler_cookies_login()

    # Faz o processamento com autenticação.
    try:
        aluno, series, logado = rn.ModeloLMSAutenticado(cred).consultar_aluno(id_aluno)
    except rn.NaoLogado:
        return redirect("/")

    # Monta a resposta.
    if aluno is None:
        return render_template("menu.html", logado = logado, mensagem = f"Esse aluno não existe."), 404
    return render_template("form_aluno.html", logado = logado, aluno = aluno, series = series)

# Processa o formulário de criação de alunos. Inclui upload de fotos.
@app.route("/aluno/novo", methods = ["POST"])
def criar_aluno_api():

    # Obtém o login e senha do cookie.
    cred = ler_cookies_login()

    # Extrai os dados do formulário.
    nome = request.form["nome"]
    sexo = request.form["sexo"]
    id_serie = request.form["id_serie"]

    # Faz o processamento.
    try:
        aluno, logado = rn.ModeloLMSAutenticado(cred).criar_aluno(nome, sexo, id_serie, salvar_arquivo_upload)
    except rn.NaoLogado:
        return redirect("/")

    # Monta a resposta.
    mensagem = f"O aluno {nome} foi criado com o id {aluno['id_aluno']}." if sexo == "M" else f"A aluna {nome} foi criada com o id {aluno['id_aluno']}."
    return render_template("menu.html", logado = logado, mensagem = mensagem)

# Processa o formulário de alteração de alunos. Inclui upload de fotos.
@app.route("/aluno/<int:id_aluno>", methods = ["POST"])
def editar_aluno_api(id_aluno):

    # Obtém o login e senha do cookie.
    cred = ler_cookies_login()

    # Extrai os dados do formulário.
    nome = request.form["nome"]
    sexo = request.form["sexo"]
    id_serie = request.form["id_serie"]

    # Faz o processamento.
    try:
        status, aluno, logado = rn.ModeloLMSAutenticado(cred).editar_aluno(id_aluno, nome, sexo, id_serie, salvar_arquivo_upload, deletar_foto)
    except rn.NaoLogado:
        return redirect("/")

    # Monta a resposta.
    if status == 'não existe':
        mensagem = "Esse aluno nem mesmo existia mais." if sexo == "M" else "Essa aluna nem mesmo existia mais."
        return render_template("menu.html", logado = logado, mensagem = mensagem), 404
    mensagem = f"O aluno {nome} com o id {id_aluno} foi editado." if sexo == "M" else f"A aluna {nome} com o id {id_aluno} foi editada."
    return render_template("menu.html", logado = logado, mensagem = mensagem)

# Processa o botão de excluir um aluno.
@app.route("/aluno/<int:id_aluno>", methods = ["DELETE"])
def deletar_aluno_api(id_aluno):

    # Obtém o login e senha do cookie.
    cred = ler_cookies_login()

    # Faz o processamento.
    try:
        aluno, logado = rn.ModeloLMSAutenticado(cred).apagar_aluno(id_aluno)
    except rn.NaoLogado:
        return redirect("/")

    # Monta a resposta.
    if aluno is None:
        return render_template("menu.html", logado = logado, mensagem = "Esse aluno nem mesmo existia mais."), 404
    mensagem = f"O aluno com o id {id_aluno} foi excluído." if aluno['sexo'] == "M" else f"A aluna com o id {id_aluno} foi excluída."
    return render_template("menu.html", logado = logado, mensagem = mensagem)

### Fotos dos alunos. ###

# Faz o download de uma foto.
@app.route("/aluno/foto/<id_foto>")
def aluno_download_foto(id_foto):

    # Obtém o login e senha do cookie.
    cred = ler_cookies_login()

    # Faz o processamento.
    try:
        logado = cred.fazer_login()
    except rn.NaoLogado:
        return redirect("/")

    # Monta a resposta.
    try:
        return send_from_directory("alunos_fotos", id_foto)
    except werkzeug.exceptions.NotFound as x:
        return send_from_directory("static", "no-photo.png")

# Deleta uma foto.
@app.route("/aluno/foto/<id_foto>", methods = ["DELETE"])
def aluno_deletar_foto(id_foto):

    # Obtém o login e senha do cookie.
    cred = ler_cookies_login()

    # Faz o processamento.
    try:
        logado = cred.fazer_login()
    except rn.NaoLogado:
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

def ler_cookies_login():
    login = request.cookies.get("login", "")
    senha = request.cookies.get("senha", "")
    return rn.Credenciais(login, senha)

########################
#### Inicialização. ####
########################

if __name__ == "__main__":
    rn.inicializar()
    app.run()