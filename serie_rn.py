import db

##########################################
#### Definições de regras de negócio. ####
##########################################

class NaoLogado(BaseException):
    pass

class Credenciais:
    def __init__(self, login, senha):
        self.__login = login
        self.__senha = senha

    def fazer_login(self):
        logado = db.fazer_login(self.__login, self.__senha)
        if logado is None:
            raise NaoLogado()
        return logado

class ModeloLMSAutenticado:

    def __init__(self, credenciais):
        self.__credenciais = credenciais

    def criar_serie(self, numero, turma):
        logado = self.__credenciais.fazer_login()
        serie_ja_existe = db.verificar_serie(numero, turma)
        if serie_ja_existe is not None: return True, serie_ja_existe
        serie_nova = db.criar_serie(numero, turma)
        return False, serie_nova, logado

    def consultar_aluno(self, id_aluno):
        logado = self.__credenciais.fazer_login()
        aluno = db.consultar_aluno(id_aluno)
        series = db.listar_series_ordem()
        return (aluno, series, logado)

    def listar_alunos(self):
        logado = self.__credenciais.fazer_login()
        return (db.listar_alunos(), logado)

    def listar_series(self):
        logado = self.__credenciais.fazer_login()
        return (db.listar_series(), logado)

    def criar_aluno(self, nome, sexo, id_serie, salvar_foto):
        logado = self.__credenciais.fazer_login()
        aluno = db.criar_aluno(nome, sexo, id_serie, salvar_foto())
        return (aluno, logado)

    def editar_aluno(self, id_aluno, nome, sexo, id_serie, salvar_foto, apagar_foto):
        logado = self.__credenciais.fazer_login()
        aluno = db.consultar_aluno(id_aluno)
        if aluno is None:
            return 'não existe', None
        id_foto = salvar_foto()
        if id_foto == "":
            id_foto = aluno["id_foto"]
        else:
            apagar_foto(aluno["id_foto"])
        db.editar_aluno(id_aluno, nome, sexo, id_serie, id_foto)
        return ('alterado', aluno, logado)

    def apagar_aluno(self, id_aluno):
        logado = self.__credenciais.fazer_login()
        aluno = db.consultar_aluno(id_aluno)
        if aluno is not None: db.deletar_aluno(id_aluno)
        return (aluno, logado)

    def listar_series_ordem(self):
        logado = self.__credenciais.fazer_login()
        return (db.listar_series_ordem(), logado)

def inicializar():
    db.inicializar()