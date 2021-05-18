from contextlib import closing
import sqlite3

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

def inicializar():
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.executescript(sql_create)
        con.commit()

def listar_series():
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("SELECT id_serie, numero, turma FROM serie")
        return rows_to_dict(cur.description, cur.fetchall())

def listar_series_ordem():
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("SELECT id_serie, numero, turma FROM serie ORDER BY numero, turma")
        return rows_to_dict(cur.description, cur.fetchall())

def verificar_serie(numero, turma):
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("SELECT id_serie, numero, turma FROM serie WHERE numero = ? AND turma = ?", [numero, turma])
        return row_to_dict(cur.description, cur.fetchone())

def consultar_aluno(id_aluno):
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("SELECT a.id_aluno, a.nome, a.sexo, a.id_serie, a.id_foto, s.numero, s.turma FROM aluno a INNER JOIN serie s ON a.id_serie = s.id_serie WHERE a.id_aluno = ?", [id_aluno])
        return row_to_dict(cur.description, cur.fetchone())

def listar_alunos():
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("SELECT a.id_aluno, a.nome, a.sexo, a.id_serie, a.id_foto, s.numero, s.turma FROM aluno a INNER JOIN serie s ON a.id_serie = s.id_serie")
        return rows_to_dict(cur.description, cur.fetchall())

def criar_serie(numero, turma):
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("INSERT INTO serie (numero, turma) VALUES (?, ?)", [numero, turma])
        id_serie = cur.lastrowid
        con.commit()
        return {'id_serie': id_serie, 'numero': numero, 'turma': turma}

def criar_aluno(nome, sexo, id_serie, id_foto):
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("INSERT INTO aluno (nome, sexo, id_serie, id_foto) VALUES (?, ?, ?, ?)", [nome, sexo, id_serie, id_foto])
        id_aluno = cur.lastrowid
        con.commit()
        return {'id_aluno': id_aluno, 'nome': nome, 'sexo': sexo, 'id_serie': id_serie, 'id_foto': id_foto}

def editar_aluno(id_aluno, nome, sexo, id_serie, id_foto):
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("UPDATE aluno SET nome = ?, sexo = ?, id_serie = ?, id_foto = ? WHERE id_aluno = ?", [nome, sexo, id_serie, id_foto, id_aluno])
        con.commit()
        return {'id_aluno': id_aluno, 'nome': nome, 'sexo': sexo, 'id_serie': id_serie, 'id_foto': id_foto}

def deletar_aluno(id_aluno):
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("DELETE FROM aluno WHERE id_aluno = ?", [id_aluno])
        con.commit()

def fazer_login(login, senha):
    with closing(conectar()) as con, closing(con.cursor()) as cur:
        cur.execute("SELECT u.login, u.senha, u.nome FROM usuario u WHERE u.login = ? AND u.senha = ?", [login, senha])
        return row_to_dict(cur.description, cur.fetchone())