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
  const saveTrigger = useRef<HTMLButtonElement>(null);
  const savedMessage = useRef<HTMLParagraphElement>(null);
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
          onClick={() => setEditing(true)}
        >
          Salvar consulta favorita
        </button>
      ) : (
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            if (!name.trim() || busy) return;
            if (await onSave(answerId, name.trim())) {
              setEditing(false);
              setName("");
              requestAnimationFrame(() => savedMessage.current?.focus());
            }
          }}
        >
          <label htmlFor={`favorite-name-${answerId}`}>
            Nome da consulta favorita
          </label>
          <input
            id={`favorite-name-${answerId}`}
            value={name}
            onChange={(event) => setName(event.target.value)}
            autoFocus
            maxLength={120}
            required
            disabled={busy}
          />
          <div className="favorite-actions">
            <button
              type="submit"
              className="primary-button"
              disabled={busy || !name.trim()}
            >
              {busy ? "Salvando…" : "Salvar favorito"}
            </button>
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={() => {
                setEditing(false);
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
