import type { RefObject } from "react";
import { Icon } from "@/components/icon";
import type { Mode } from "@/lib/contracts";

type ComposerProps = {
  mode: Mode;
  llmAvailable: boolean;
  hasPlan: boolean;
  reviewingEarlier: boolean;
  busy: boolean;
  periodInvalid: boolean;
  question: string;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  onQuestionChange: (question: string) => void;
  onAsk: (question: string) => void;
};

export function QuestionComposer({
  mode,
  llmAvailable,
  hasPlan,
  reviewingEarlier,
  busy,
  periodInvalid,
  question,
  textareaRef,
  onQuestionChange,
  onAsk,
}: ComposerProps) {
  const canSend =
    !busy &&
    !periodInvalid &&
    question.trim().length > 0 &&
    !(mode === "llm" && !llmAvailable);
  return (
    <div className="composer-container">
      {reviewingEarlier && (
        <p className="reviewing-note">
          Você está revendo um resultado anterior. A continuação usa o último
          plano válido desta conversa.
        </p>
      )}
      {mode === "llm" && !llmAvailable && (
        <div className="notice warning" role="status">
          A interpretação com IA não está disponível. Selecione demonstração
          para continuar consultando os dados.
        </div>
      )}
      {hasPlan && (
        <button
          className="followup"
          onClick={() => onAsk("E nos sete dias anteriores?")}
          disabled={busy || periodInvalid || (mode === "llm" && !llmAvailable)}
        >
          <Icon name="clock" size={14} />E nos sete dias anteriores?
          <Icon name="arrow" size={14} />
        </button>
      )}
      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          if (canSend) onAsk(question);
        }}
      >
        <label htmlFor="question" className="composer-label">
          Pergunta
        </label>
        <textarea
          id="question"
          ref={textareaRef}
          value={question}
          placeholder="Ex.: quanto vendi ontem?"
          onChange={(event) => onQuestionChange(event.target.value)}
          onFocus={(event) => {
            const field = event.currentTarget;
            const bounds = field.getBoundingClientRect();
            if (bounds.top < 0 || bounds.bottom > window.innerHeight)
              field.scrollIntoView({
                block: "center",
                inline: "nearest",
                behavior: "instant",
              });
          }}
          onKeyDown={(event) => {
            if (event.nativeEvent.isComposing) return;
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              if (canSend) onAsk(question);
            }
          }}
          maxLength={1000}
          aria-describedby="question-guidance"
          rows={3}
          disabled={busy}
        />
        <div className="composer-bottom">
          <span>
            <span className="status-dot" />
            {mode === "demo" ? "Demo sem IA" : "Interpretação com IA"}
          </span>
          <button
            type="submit"
            className="send-button"
            aria-label="Enviar pergunta"
            disabled={!canSend}
          >
            <span>{busy ? "Consultando" : "Consultar"}</span>
            {busy ? (
              <span className="spinner" />
            ) : (
              <Icon name="arrow" size={19} />
            )}
          </button>
        </div>
      </form>
      <p id="question-guidance" className="composer-footnote">
        Enter envia · Shift + Enter quebra linha · {question.length}/1000
        caracteres
      </p>
    </div>
  );
}
