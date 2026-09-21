import { Icon } from "@/components/icon";
import type { Mode, Period, Store } from "@/lib/contracts";
import { periodLabel } from "@/lib/format";

type FiltersProps = {
  stores: Store[];
  storeIds: string[];
  period: Period | null;
  periodPreset: string;
  mode: Mode;
  llmAvailable: boolean;
  busy: boolean;
  periodInvalid: boolean;
  onStoresChange: (ids: string[]) => void;
  onPresetChange: (preset: string) => void;
  onModeChange: (mode: Mode) => void;
  onPeriodChange: (period: Period) => void;
};

export function AnalysisFilters({
  stores,
  storeIds,
  period,
  periodPreset,
  mode,
  llmAvailable,
  busy,
  periodInvalid,
  onStoresChange,
  onPresetChange,
  onModeChange,
  onPeriodChange,
}: FiltersProps) {
  return (
    <>
      <div
        className="filters"
        role="group"
        aria-label="Filtros da próxima consulta"
      >
        <div className="filter-field store-filter">
          <label htmlFor="store-filter">
            <Icon name="store" size={15} />
            Loja
          </label>
          <select
            id="store-filter"
            value={storeIds.length === 1 ? storeIds[0] : "all"}
            onChange={(event) =>
              onStoresChange(
                event.target.value === "all"
                  ? stores.map((store) => store.id)
                  : [event.target.value],
              )
            }
            disabled={busy}
          >
            {stores.length > 1 && (
              <option value="all">Todas as minhas lojas</option>
            )}
            {stores.map((store) => (
              <option value={store.id} key={store.id}>
                {store.name}
              </option>
            ))}
          </select>
        </div>
        <div className="filter-field">
          <label htmlFor="period-filter">
            <Icon name="calendar" size={15} />
            Período
          </label>
          <select
            id="period-filter"
            value={periodPreset}
            onChange={(event) => onPresetChange(event.target.value)}
            disabled={busy}
          >
            <option value="question">Definido pela pergunta</option>
            <option value="yesterday">Ontem</option>
            <option value="week">Últimos 7 dias</option>
            <option value="month">Últimos 30 dias</option>
            <option value="custom">Personalizado</option>
            {periodPreset === "effective" && (
              <option value="effective">
                {period ? periodLabel(period) : "Período interpretado"}
              </option>
            )}
          </select>
        </div>
        <div className="filter-field mode-filter">
          <label htmlFor="mode-filter">
            <Icon name="spark" size={15} />
            Interpretador
          </label>
          <select
            id="mode-filter"
            value={mode}
            onChange={(event) => onModeChange(event.target.value as Mode)}
            disabled={busy}
          >
            <option value="demo">Demonstração (sem IA)</option>
            <option value="llm">
              Modelo de IA{!llmAvailable ? " · indisponível" : ""}
            </option>
          </select>
        </div>
      </div>
      <p className="filter-guidance">
        Datas escritas na pergunta prevalecem sobre o filtro.
      </p>
      {period && periodPreset === "custom" && (
        <div className="effective-period">
          <label>
            Início (incluído)
            <input
              type="date"
              min="0001-01-01"
              max="9999-12-31"
              aria-invalid={periodInvalid}
              aria-describedby={periodInvalid ? "period-error" : undefined}
              value={period.start}
              onChange={(event) =>
                onPeriodChange({ ...period, start: event.target.value })
              }
              disabled={busy}
            />
          </label>
          <label>
            Fim (excluído)
            <input
              type="date"
              min="0001-01-01"
              max="9999-12-31"
              aria-invalid={periodInvalid}
              aria-describedby={periodInvalid ? "period-error" : undefined}
              value={period.end}
              onChange={(event) =>
                onPeriodChange({ ...period, end: event.target.value })
              }
              disabled={busy}
            />
          </label>
          <small>Máximo: 90 dias.</small>
        </div>
      )}{" "}
      {periodInvalid && (
        <div
          id="period-error"
          className="notice danger workspace-notice"
          role="alert"
        >
          Use 1 a 90 dias, com fim posterior ao início.
        </div>
      )}
    </>
  );
}
