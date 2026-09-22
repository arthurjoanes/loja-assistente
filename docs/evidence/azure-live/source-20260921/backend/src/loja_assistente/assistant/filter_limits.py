"""Reject explicit filters that cannot be represented by the analytics contract."""

import re
import unicodedata


def normalize(value: str) -> str:
    folded = "".join(
        letter
        for letter in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(letter)
    )
    return " ".join(folded.split())


def without_conversational_prefix(question: str) -> str:
    text = normalize(question)
    text = re.sub(r"^(?:oi|ola|bom dia|boa tarde|boa noite)\b[\s,!.:;-]*", "", text)
    text = re.sub(
        r"^(?:por favor|(?:eu )?(?:so )?(?:queria|quero|gostaria de) saber|"
        r"(?:voce )?pode me (?:mostrar|dizer)|me (?:mostra|mostre))\b[\s,!:;-]*",
        "",
        text,
    )
    return text.strip()


def unsupported_filter(question: str) -> str | None:
    # Remove only an anchored conversational prefix. A qualifier later in the request stays visible.
    text = without_conversational_prefix(question)
    if re.search(
        r"\b(?:dinheiro|pix|cartao|cartoes|credito|debito|boleto|pagamento|pagamentos|"
        r"vendedor|vendedora|vendedores|categoria|categorias|canal|canais|cupom|cupons)\b",
        text,
    ):
        return "Filtro não suportado. Use loja e período; não há filtros por pagamento, vendedor, categoria, canal ou cupom."
    if re.search(
        r"\b(?:exceto|excluindo|excluir|tirando|apenas|somente|so|sem|acima|abaixo|"
        r"maior que|menor que|entre valores)\b",
        text,
    ):
        return "Exclusões e condições adicionais não são suportadas. Use loja e período."
    if re.search(
        r"\b(?:horas?|horarios?|manha|tarde|noite|madrugada)\b"
        r"|\b\d{1,2}(?::\d{2}|h(?:\d{2})?)\b",
        text,
    ):
        return "Não há filtro por horário. As consultas usam dias completos em America/Sao_Paulo."
    if re.search(r"\b(?:d[oa]|pel[oa]|para (?:o|a))\s+produto\b", text):
        return "Não há filtro por produto. Use o ranking por receita ou unidades."
    return None
