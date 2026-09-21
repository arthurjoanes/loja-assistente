import type { RefObject } from "react";
import { Icon } from "@/components/icon";
import type { Mode } from "@/lib/contracts";

type ComposerProps = {
  mode: Mode;
  llmAvailable: boolean;
  hasPlan: boolean;
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
      {mode === "llm" && !llmAvailable && (
        <div className="notice warning" role="status">
          Provedor indisponível. Configure a integração no servidor ou selecione
          demo.
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
        <label htmlFor="question" className="sr-only">
          Pergunta
        </label>
        <textarea
          id="question"
          ref={textareaRef}
          value={question}
          placeholder="Ex.: quanto vendi ontem?"
          onChange={(event) => onQuestionChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              if (canSend) onAsk(question);
            }
          }}
          maxLength={1000}
          aria-describedby="question-guidance"
          rows={2}
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
