"""Validação e normalização dos dados pessoais pedidos no cadastro."""

import re
import unicodedata

UFS = (
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA',
    'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
)


def somente_digitos(valor) -> str:
    return re.sub(r'\D', '', str(valor or ''))


def cpf_valido(cpf: str) -> bool:
    """CPF com 11 dígitos, não repetido (000.000.000-00 etc.) e dígitos verificadores corretos."""
    cpf = somente_digitos(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10 % 11) % 10
        if digito != int(cpf[tamanho]):
            return False
    return True


def chave_cidade(nome) -> str:
    """'São Paulo ' e 'sao paulo' viram a mesma chave: sem acento, minúsculas, espaços únicos."""
    sem_acento = unicodedata.normalize('NFKD', str(nome or '')).encode('ascii', 'ignore').decode()
    return ' '.join(sem_acento.lower().split())
