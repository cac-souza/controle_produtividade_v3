# helpers.py - 
from modelos import Usuario

def usuarios_visiveis(usuario_logado, session):
    papel = usuario_logado.papel.lower()
    visiveis = []
    if papel == "admin":
        visiveis = session.query(Usuario).filter(Usuario.login != "admin").all()
    elif papel == "gestor":
        visiveis = session.query(Usuario).filter(
            Usuario.setor_id == usuario_logado.setor_id,
            Usuario.login != "admin"
        ).all()
    elif papel in ("lider", "chefe"):
        visiveis = session.query(Usuario).filter(
            Usuario.equipe_id == usuario_logado.equipe_id,
            Usuario.login != "admin"
        ).all()
    elif papel == "fiscal":
        visiveis = [usuario_logado]
    if usuario_logado not in visiveis:
        visiveis.append(usuario_logado)
    return visiveis

