import { Icon } from "@/components/icon";

const suggestions = [
  {
    icon: "store" as const,
    title: "Receita de ontem",
    description: "Receita líquida da sua loja",
    question: "Quanto vendi ontem?",
  },
  {
    icon: "chart" as const,
    title: "Ranking de produtos",
    description: "Top 5 produtos por receita",
    question: "Quais os 5 produtos com maior receita nos últimos 7 dias?",
  },
  {
    icon: "calendar" as const,
    title: "Evolução diária",
    description: "Receita de cada um dos últimos 7 dias",
    question: "Mostre a evolução diária da receita nos últimos 7 dias",
  },
  {
    icon: "grid" as const,
    title: "Ticket médio",
    description: "Valor médio por pedido concluído",
    question: "Qual foi o ticket médio ontem?",
  },
  {
    icon: "clock" as const,
    title: "Comparação de períodos",
    description: "Compare dois períodos equivalentes",
    question: "Compare a receita dos últimos 7 dias com o período anterior",
  },
  {
    icon: "list" as const,
    title: "Unidades vendidas",
    description: "Quantidade vendida ontem",
    question: "Quantas unidades vendi ontem?",
  },
];

export function AnalysisStart({
  disabled,
  onAsk,
}: {
  disabled: boolean;
  onAsk: (question: string) => void;
}) {
  return (
    <section className="welcome">
      <span className="eyebrow">Consultas disponíveis</span>
      <h2>Comece por uma pergunta de negócio.</h2>
      <p className="welcome-description">
        Escolha uma consulta abaixo ou use o campo Pergunta. O resultado reúne o
        indicador, seu recorte e o cálculo que permite conferir os números.
      </p>

      <div className="suggestions">
        {suggestions.map((item) => (
          <button
            key={item.title}
            onClick={() => onAsk(item.question)}
            disabled={disabled}
          >
            <span className="suggestion-icon">
              <Icon name={item.icon} size={19} />
            </span>
            <strong>{item.title}</strong>
            <span>{item.description}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
