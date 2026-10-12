"use client";
import { useRef, useState } from "react";

export function SaveFavorite({
  answerId,
  busy,
  saved,
  onSave,
}: {
  answerId: string;
  busy: boolean;
  saved: boolean;
  onSave: (answerId: string, name: string) => Promise<boolean>;
}) {
  const [name, setName] = useState("");
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [invalidName, setInvalidName] = useState(false);
  const saveTrigger = useRef<HTMLButtonElement>(null);
  const savedMessage = useRef<HTMLParagraphElement>(null);
  const nameInput = useRef<HTMLInputElement>(null);
  const errorNotice = useRef<HTMLParagraphElement>(null);
  if (saved)
    return (
      <p
        className="saved-favorite"
        role="status"
        ref={savedMessage}
        tabIndex={-1}
      >
        Consulta salva nos favoritos.
      </p>
    );
  return (
    <div className="save-favorite">
      {!editing ? (
        <button
          className="text-button"
          ref={saveTrigger}
          disabled={busy}
          onClick={() => {
            setError(null);
            setInvalidName(false);
            setEditing(true);
            requestAnimationFrame(() => nameInput.current?.focus());
          }}
        >
          Salvar consulta favorita
        </button>
      ) : (
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            if (busy) return;
            if (!name.trim()) {
              setInvalidName(true);
              setError("Dê um nome à consulta para salvar nos favoritos.");
              nameInput.current?.focus();
              return;
            }
            setInvalidName(false);
            setError(null);
            if (await onSave(answerId, name.trim())) {
              setEditing(false);
              setName("");
              requestAnimationFrame(() => savedMessage.current?.focus());
            } else {
              setError(
                "Não foi possível confirmar o salvamento. Confira a mensagem de erro e tente salvar novamente.",
              );
              requestAnimationFrame(() => {
                if (nameInput.current?.disabled) errorNotice.current?.focus();
                else nameInput.current?.focus();
              });
            }
          }}
        >
          <label htmlFor={`favorite-name-${answerId}`}>
            Nome da consulta favorita
          </label>
          <input
            id={`favorite-name-${answerId}`}
            name="favorite_name"
            autoComplete="off"
            ref={nameInput}
            value={name}
            onChange={(event) => {
              setName(event.target.value);
              setError(null);
              setInvalidName(false);
            }}
            aria-invalid={invalidName}
            aria-describedby={
              error
                ? `favorite-error-${answerId}`
                : `favorite-guidance-${answerId}`
            }
            maxLength={120}
            required
            disabled={busy}
          />
          <p id={`favorite-guidance-${answerId}`} className="field-hint">
            Use um nome que ajude a reconhecer esta consulta. Máximo: 120
            caracteres.
          </p>
          {error && (
            <p
              id={`favorite-error-${answerId}`}
              className="field-error"
              role="alert"
              ref={errorNotice}
              tabIndex={-1}
            >
              {error}
            </p>
          )}
          <div className="favorite-actions">
            <button type="submit" className="primary-button" disabled={busy}>
              {busy ? "Salvando…" : "Salvar favorito"}
            </button>
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={() => {
                setEditing(false);
                setError(null);
                requestAnimationFrame(() => saveTrigger.current?.focus());
              }}
            >
              Cancelar
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
