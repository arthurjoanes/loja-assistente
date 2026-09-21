"""Renderiza os logs Azure já salvos; Python 3.11+, somente biblioteca padrão.

Não importa a aplicação nem lê .env; não chama APIs ou executa avaliações. Use --write
para atualizar as duas páginas derivadas ou --check para verificar seus bytes.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/evidence/azure-live"
RUNS = (
    ("smoke", "20260921T121119Z-883376fa", 1),
    ("development", "20260921T121149Z-c53a402a", 12),
    ("final", "20260921T121255Z-a9c11d1f", 42),
)
INPUT_RATE = Decimal("0.25")
OUTPUT_RATE = Decimal("1.20")


@dataclass(frozen=True)
class Record:
    line: int
    data: dict[str, Any]


@dataclass(frozen=True)
class Run:
    stage: str
    run_id: str
    summary: dict[str, Any]
    records: list[Record]

    def link(self, filename: str, line: int | None = None) -> str:
        suffix = "" if line is None else f"#L{line}"
        return f"../../../evals/reports/{self.run_id}/{filename}{suffix}"

    def calls(self) -> list[tuple[Record, dict[str, Any]]]:
        return [(record, call) for record in self.records for call in record.data["provider"]]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_runs() -> list[Run]:
    runs = []
    all_call_ids: set[str] = set()
    for stage, run_id, expected_calls in RUNS:
        directory = ROOT / "evals/reports" / run_id
        summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
        records = [
            Record(line, json.loads(value))
            for line, value in enumerate(
                (directory / "cases.jsonl").read_text(encoding="utf-8").splitlines(), 1
            )
            if value.strip()
        ]
        run = Run(stage, run_id, summary, records)
        require(summary["run_id"] == run_id and summary["stage"] == stage, f"Run incorreto: {run_id}")
        require(summary["mode"] == "live", f"Run sem inferência live: {run_id}")
        require(summary["exit_code"] == 0, f"Run incompleto: {run_id}")
        keys = [(r.data["id"], r.data["repetition"], r.data["mode"]) for r in records]
        require(len(set(keys)) == len(keys), f"Registros duplicados: {run_id}")
        require(set(key[2] for key in keys) == {"demo", "structured", "llm"}, f"Modos: {run_id}")
        for mode, measured in summary["summaries"].items():
            selected = [r.data for r in records if r.data["mode"] == mode]
            require(len(selected) == measured["executed"], f"Contagem {mode}: {run_id}")
            passed = sum(row["assessment"]["passed"] for row in selected)
            require(passed == measured["passed"], f"Acertos {mode}: {run_id}")
            require(len(selected) - passed == measured["failed"], f"Falhas {mode}: {run_id}")
        calls = run.calls()
        require(len(calls) == summary["live_model_calls"] == expected_calls, f"Chamadas: {run_id}")
        usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        for record, call in calls:
            require(record.data["mode"] == "llm", f"Provedor fora do modo LLM: {run_id}")
            require(call["call_id"] not in all_call_ids, "call_id duplicado entre runs")
            all_call_ids.add(call["call_id"])
            require(call["status"] == "completed" and call["attempts"] == 1, "Chamada não concluída")
            require(bool(call["provider_request_id"]) and bool(call["response_id"]), "IDs ausentes")
            require(call["model_returned"] == call["model_requested"] == summary["deployment"], "Modelo divergente")
            for field in usage:
                value = call[field]
                require(type(value) is int and value >= 0, f"Uso desconhecido: {field}")
                usage[field] += value
            require(call["input_tokens"] + call["output_tokens"] == call["total_tokens"], "Tokens da chamada divergem")
        for field, value in usage.items():
            require(value == summary["measured_usage"][field], f"Uso {field}: {run_id}")
        require(summary["measured_usage"]["unknown_usage_calls"] == 0, "Há uso não medido")
        cost = (usage["input_tokens"] * INPUT_RATE + usage["output_tokens"] * OUTPUT_RATE) / 1_000_000
        require(cost == Decimal(summary["estimated_known_usage_usd"]), f"Custo estimado: {run_id}")
        llm = [r.data for r in records if r.data["mode"] == "llm"]
        invoked = sum(bool(row["provider"]) for row in llm)
        require(invoked == summary["summaries"]["llm"]["provider_invoked_cases"], "Casos com provedor divergem")
        require(len(llm) - invoked == summary["summaries"]["llm"]["local_guard_cases"], "Guardas locais divergem")
        runs.append(run)
    final = runs[-1]
    llm = [r for r in final.records if r.data["mode"] == "llm"]
    require(len(llm) == 48 and len({r.data["id"] for r in llm}) == 24, "Final deve ter 24 perguntas e 48 execuções")
    require({r.data["repetition"] for r in llm} == {1, 2}, "Repetições finais incorretas")
    return runs


def cell(value: object) -> str:
    return html.escape(str(value), quote=False).replace("|", "&#124;").replace("\n", "<br>")


def row(values: list[object]) -> str:
    return "| " + " | ".join(str(value) for value in values) + " |"


def anchor(record: Record) -> str:
    return f"case-{record.data['id']}-r{record.data['repetition']}"


def verdict(run: Run, record: Record | None) -> str:
    if record is None:
        return "N/A"
    label = "PASSOU" if record.data["assessment"]["passed"] else "FALHOU"
    return f"[{label}]({run.link('cases.jsonl', record.line)})"


def received_status(record: Record) -> str:
    status = record.data["observed"].get("status")
    return f"`{cell(status)}`" if status is not None else "Sem campo status"


def generated_note() -> list[str]:
    return [
        "Página derivada dos registros originais. Gerador: [render_evidence.py](../../../scripts/render_evidence.py).",
        "Para conferir offline, na raiz do repositório: `python scripts/render_evidence.py --check`.",
        "Para regenerar: `python scripts/render_evidence.py --write`. Requer Python 3.11+; não usa SDK, Docker, chave ou rede.",
        "",
    ]


def render_cases(run: Run) -> bytes:
    llm = [r for r in run.records if r.data["mode"] == "llm"]
    indexed = {(r.data["id"], r.data["repetition"], r.data["mode"]): r for r in run.records}
    summaries = run.summary["summaries"]
    failed = [r for r in llm if not r.data["assessment"]["passed"]]
    lines = [
        "# Avaliação final, caso a caso",
        "",
        "[Resultado e método](../../azure-live-results.md) · [Chamadas Azure](calls.md)",
        "",
        f"Run `{run.run_id}` · início UTC `{run.summary['started_at']}` · fim UTC `{run.summary['finished_at']}`.",
        f"Fonte: [JSONL original]({run.link('cases.jsonl')}) e [resumo original]({run.link('summary.json')}).",
        "",
        f"**{len(llm)} execuções de 24 perguntas, duas repetições por pergunta.** "
        f"Parser: {summaries['demo']['passed']}/{summaries['demo']['executed']}; "
        f"entrada estruturada: {summaries['structured']['passed']}/{summaries['structured']['executed']} aplicáveis; "
        f"fluxo LLM: {summaries['llm']['passed']}/{summaries['llm']['executed']}.",
        "",
        f"O fluxo LLM inclui **{summaries['llm']['provider_invoked_cases']} chamadas Azure** e "
        f"**{summaries['llm']['local_guard_cases']} decisões de guarda local**, sem chamada ao modelo. "
        "As repetições não são perguntas independentes. Os dados e as identidades são sintéticos.",
        "",
        "`PASSOU` significa que a avaliação do resultado correspondeu ao esperado; uma recusa correta também passa. "
        "`N/A` significa que o modo estruturado não se aplica, sem pontuar como acerto. "
        "O estado recebido e o tempo abaixo são do fluxo LLM, incluindo aplicação, autorização, PostgreSQL e, quando chamada, Azure. "
        "Não são latência do navegador ou SLA de produção.",
        "",
        "## Falha preservada",
        "",
    ]
    for record in failed:
        data = record.data
        lines.extend([
            f"- [{data['id']}, repetição {data['repetition']}](#{anchor(record)}): "
            f"estado `{data['observed'].get('status')}`; "
            f"falhas de avaliação `{', '.join(data['assessment']['failures'])}`; "
            f"`unnecessary_clarification={str(data['assessment']['unnecessary_clarification']).lower()}`; "
            f"`sales_queries={data['sales_queries']}`.",
        ])
    lines.extend([
        "",
        "A falha permanece nos totais e no registro original. A resposta pediu um esclarecimento desnecessário sobre dias sem carga; "
        "o plano esperado permitiria calcular R$ 25,00 e informar cobertura parcial (5 de 6 dias). "
        "A repetição 1 da mesma pergunta passou. Nenhum ajuste ou nova inferência foi executado para gerar esta página.",
        "",
        "## Comparação das 48 execuções",
        "",
        "Cada resultado abre a linha correspondente do JSONL; o ID abre os detalhes do fluxo LLM nesta página.",
        "",
        row(["Caso", "Rep.", "Pergunta", "Parser", "Estruturado", "LLM", "Origem", "Estado recebido / HTTP", "Fluxo (ms)"]),
        row(["---"] * 9),
    ])
    for record in llm:
        data = record.data
        key = (data["id"], data["repetition"])
        lines.append(row([
            f"[{data['id']}](#{anchor(record)})", data["repetition"], cell(data["question"]),
            verdict(run, indexed[(*key, "demo")]), verdict(run, indexed.get((*key, "structured"))),
            verdict(run, record), "Azure" if data["provider"] else "Guarda local",
            f"{received_status(record)} / {data['http_status']}", data["duration_ms"],
        ]))
    lines.extend(["", "## Detalhes dos registros LLM", ""])
    for record in llm:
        data = record.data
        subset = {key: data[key] for key in ("expected", "observed", "assessment", "sales_queries", "provider")}
        lines.extend([
            f'<a id="{anchor(record)}"></a>',
            "<details>",
            f"<summary>{cell(data['id'])} · repetição {data['repetition']} · "
            f"{'PASSOU' if data['assessment']['passed'] else 'FALHOU'} · {cell(data['category'])}</summary>",
            "",
            f"**Pergunta:** {cell(data['question'])}",
            "",
            f"[Registro original, linha {record.line}]({run.link('cases.jsonl', record.line)}) · "
            f"identidade sintética `{data['identity']}` · HTTP `{data['http_status']}` · fluxo `{data['duration_ms']} ms`.",
            "",
            "`expected` é o gabarito; `observed` é a resposta da aplicação; `assessment` é a avaliação determinística. "
            "`sales_queries` conta as consultas analíticas às vendas. `provider` contém somente os metadados permitidos da chamada; "
            "lista vazia identifica decisão da guarda local.",
            "",
            "```json",
            json.dumps(subset, ensure_ascii=False, indent=2),
            "```",
            "",
            "</details>",
            "",
        ])
    lines.extend(generated_note())
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def render_calls(runs: list[Run]) -> bytes:
    count = sum(len(run.calls()) for run in runs)
    inputs = sum(call["input_tokens"] for run in runs for _, call in run.calls())
    outputs = sum(call["output_tokens"] for run in runs for _, call in run.calls())
    cost = sum((Decimal(run.summary["estimated_known_usage_usd"]) for run in runs), Decimal(0))
    lines = [
        "# Registro legível das chamadas Azure",
        "",
        "[Resultado e método](../../azure-live-results.md) · [48 execuções finais](cases.md)",
        "",
        f"**{count} chamadas reais registradas**, com {inputs:,} tokens de entrada, {outputs:,} de saída "
        f"e {inputs + outputs:,} no total. Cada chamada terminou como `completed`, com `attempts=1` e uso conhecido. "
        "Os separadores numéricos desta página seguem o formato dos logs (vírgula para milhares, ponto para decimais).",
        "",
        "As linhas abaixo vêm dos três runs oficiais de 21/09/2026. "
        "O gerador confere chamadas, tokens e estimativa de custo contra o `summary.json` de cada run. "
        "Não soma `budget.calls_reserved`, tokens reservados ou custos reservados: esses campos são cumulativos entre etapas.",
        "",
        f"**Estimativa conservadora total: US$ {cost:f}.** "
        f"Cálculo: `({inputs} × {INPUT_RATE} + {outputs} × {OUTPUT_RATE}) / 1.000.000`. "
        "Adota US$ 0.25 por milhão para toda entrada (incluindo margem para cache write) e US$ 1.20 para saída. "
        "Os [preços salvos](azure-prices.json) foram consultados antes do experimento. "
        "**Estimativa não é fatura**; não houve conferência do faturamento Azure.",
        "",
        "`provider_request_id` e `response_id` são identificadores de rastreabilidade retornados pelo serviço, **não credenciais**. "
        "Eles permitem correlação por alguém com acesso autorizado aos registros Azure; sua presença nestes arquivos "
        "não constitui verificação independente no provedor. O repositório preserva o registro do cliente, sem corpo bruto da API, "
        "cabeçalhos de autenticação ou conteúdo de raciocínio do modelo.",
        "",
        "`Duração provedor` é o intervalo medido pelo adaptador local ao chamar o serviço, incluindo comunicação e SDK; "
        "não é uma métrica interna de processamento da Azure. O tempo completo da aplicação está na página de casos.",
        "",
        "## Somas por etapa",
        "",
        row(["Etapa / fonte", "Início UTC", "Chamadas", "Entrada", "Saída", "Total", "Estimativa US$"]),
        row(["---"] * 7),
    ]
    for run in runs:
        usage = run.summary["measured_usage"]
        lines.append(row([
            f"[{run.stage}]({run.link('summary.json')})", f"`{run.summary['started_at']}`",
            len(run.calls()), usage["input_tokens"], usage["output_tokens"], usage["total_tokens"],
            run.summary["estimated_known_usage_usd"],
        ]))
    lines.extend([
        row(["**Total**", "—", f"**{count}**", f"**{inputs}**", f"**{outputs}**", f"**{inputs + outputs}**", f"**{cost:f}**"]),
        "",
        "O final possui 48 execuções do fluxo LLM e 42 chamadas Azure. As seis decisões de guarda local "
        "não geraram chamadas e, portanto, não aparecem nesta tabela de consumo.",
        "",
        "## Todas as 55 chamadas",
        "",
        "A coluna de origem abre a linha exata do JSONL que contém a pergunta, o resultado e os metadados completos permitidos.",
        "",
        row(["#", "Etapa", "Caso", "Rep.", "Modelo retornado", "provider_request_id", "response_id", "Entrada", "Saída", "Duração provedor (ms)", "Origem"]),
        row(["---"] * 11),
    ])
    number = 0
    for run in runs:
        for record, call in run.calls():
            number += 1
            data = record.data
            lines.append(row([
                number, run.stage, data["id"], data["repetition"], f"`{cell(call['model_returned'])}`",
                f"`{cell(call['provider_request_id'])}`", f"`{cell(call['response_id'])}`",
                call["input_tokens"], call["output_tokens"], call["duration_ms"],
                f"[JSONL L{record.line}]({run.link('cases.jsonl', record.line)})",
            ]))
    lines.extend(["", *generated_note()])
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="Compara bytes; falha se houver divergência, sem escrever.")
    action.add_argument("--write", action="store_true", help="Gera as duas páginas a partir dos registros existentes.")
    arguments = parser.parse_args()
    try:
        runs = load_runs()
        outputs = {"cases.md": render_cases(runs[-1]), "calls.md": render_calls(runs)}
        if arguments.write:
            for name, content in outputs.items():
                (OUTPUT / name).write_bytes(content)
            print("Geradas cases.md (48 execuções) e calls.md (55 chamadas); fontes e totais conferidos.")
            return 0
        mismatches = [name for name, content in outputs.items() if not (OUTPUT / name).is_file() or (OUTPUT / name).read_bytes() != content]
        if mismatches:
            print("Divergência nas páginas derivadas: " + ", ".join(mismatches), file=sys.stderr)
            print("Revise as fontes e execute --write para regenerar. Nenhum arquivo foi alterado.", file=sys.stderr)
            return 1
        print("OK: 2 páginas idênticas byte a byte; 48 execuções, 55 chamadas e somas conferidas. Sem escrita ou rede.")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Não foi possível validar/renderizar a evidência: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
