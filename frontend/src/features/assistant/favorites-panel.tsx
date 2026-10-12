"use client";
import { useRef, useState, type RefObject } from "react";
import type { Favorite, Store } from "@/lib/contracts";
import { PlanScope } from "./plan-scope";

type FavoriteActions = {
  busy: boolean;
  conflict: boolean;
  stores: Store[];
  onRename: (favorite: Favorite, name: string) => Promise<boolean>;
  onDelete: (favorite: Favorite) => Promise<boolean>;
  onRun: (favorite: Favorite) => void;
  onOpen: (favorite: Favorite) => void;
};
function FavoriteItem({
  favorite,
  busy,
  conflict,
  stores,
  onRename,
  onDelete,
  onRun,
  onOpen,
  returnFocusTo,
}: FavoriteActions & {
  favorite: Favorite;
  returnFocusTo: RefObject<HTMLButtonElement | null>;
}) {
  const [action, setAction] = useState<"rename" | "delete" | null>(null);
  const [name, setName] = useState(favorite.name);
  const [nameError, setNameError] = useState<string | null>(null);
  const renameTrigger = useRef<HTMLButtonElement>(null);
  const deleteTrigger = useRef<HTMLButtonElement>(null);
  const renameInput = useRef<HTMLInputElement>(null);
  const deleteConfirm = useRef<HTMLButtonElement>(null);
  function cancelAction() {
    const target = action === "rename" ? renameTrigger : deleteTrigger;
    setAction(null);
    setNameError(null);
    requestAnimationFrame(() => target.current?.focus());
  }
  const locked = busy || conflict;
  return (
    <article
      className="favorite-item"
      aria-labelledby={`favorite-${favorite.id}`}
      data-testid="favorite"
    >
      <div className="favorite-heading">
        <h3 id={`favorite-${favorite.id}`}>{favorite.name}</h3>
        <p className="favorite-saved-at">
          Salva em{" "}
          <time dateTime={favorite.created_at}>
            {new Date(favorite.created_at).toLocaleString("pt-BR", {
              timeZone: "America/Sao_Paulo",
              dateStyle: "short",
              timeStyle: "short",
            })}
          </time>
          . Revisão {favorite.revision}.
        </p>
      </div>
      <PlanScope plan={favorite.plan} stores={stores} />
      <p className="scope-guidance">
        As datas deste favorito são fixas. Mudar os filtros de outra consulta
        mantém este recorte.
      </p>
      {action === "rename" ? (
        <form
          noValidate
          className="favorite-edit"
          onKeyDown={(event) => {
            if (event.key === "Escape" && !busy) {
              event.preventDefault();
              cancelAction();
            }
          }}
          onSubmit={async (event) => {
            event.preventDefault();
            if (locked) return;
            if (!name.trim()) {
              setNameError("Informe um nome para o favorito.");
              renameInput.current?.focus();
              return;
            }
            setNameError(null);
            if (await onRename(favorite, name.trim())) cancelAction();
          }}
        >
          <label htmlFor={`rename-${favorite.id}`}>Novo nome do favorito</label>
          <input
            id={`rename-${favorite.id}`}
            name="favorite-name"
            autoComplete="off"
            ref={renameInput}
            value={name}
            onChange={(event) => {
              setName(event.target.value);
              if (nameError) setNameError(null);
            }}
            maxLength={120}
            required
            disabled={locked}
            aria-invalid={Boolean(nameError)}
            aria-describedby={`rename-hint-${favorite.id}${nameError ? ` rename-error-${favorite.id}` : ""}`}
          />
          <p id={`rename-hint-${favorite.id}`} className="field-hint">
            Use até 120 caracteres para identificar esta consulta.
          </p>
          {nameError && (
            <p
              id={`rename-error-${favorite.id}`}
              className="field-error"
              role="alert"
            >
              {nameError}
            </p>
          )}
          <div className="favorite-actions">
            <button type="submit" className="primary-button" disabled={locked}>
              Confirmar novo nome
            </button>
            <button
              type="button"
              className="text-button"
              onClick={cancelAction}
              disabled={busy}
            >
              Cancelar alteração
            </button>
          </div>
        </form>
      ) : action === "delete" ? (
        <div
          className="favorite-confirmation"
          role="group"
          aria-label="Confirmar exclusão do favorito"
          onKeyDown={(event) => {
            if (event.key === "Escape" && !busy) {
              event.preventDefault();
              cancelAction();
            }
          }}
        >
          <p>
            Excluir o favorito “{favorite.name}”? O cálculo registrado continua
            no histórico.
          </p>
          <div className="favorite-actions">
            <button
              className="text-button danger-action"
              ref={deleteConfirm}
              disabled={locked}
              onClick={async () => {
                if (await onDelete(favorite))
                  requestAnimationFrame(() => returnFocusTo.current?.focus());
              }}
            >
              Confirmar exclusão
            </button>
            <button
              className="text-button"
              disabled={busy}
              onClick={cancelAction}
            >
              Manter favorito
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="favorite-task-actions">
            <div>
              <button
                className="primary-button"
                disabled={locked}
                onClick={() => onRun(favorite)}
              >
                Executar novamente
              </button>
              <p>
                Consulta a base atual com estas lojas e datas; registra outro
                cálculo.
              </p>
            </div>
            <div>
              <button
                className="text-button"
                disabled={locked}
                onClick={() => onOpen(favorite)}
              >
                Abrir cálculo registrado
              </button>
              <p>
                Abre o resultado salvo na data indicada, sem executar a
                consulta.
              </p>
            </div>
          </div>
          <div
            className="favorite-actions favorite-management"
            role="group"
            aria-label={`Alterar favorito ${favorite.name}`}
          >
            <button
              className="text-button"
              disabled={locked}
              onClick={() => {
                setName(favorite.name);
                setNameError(null);
                setAction("rename");
                requestAnimationFrame(() => renameInput.current?.focus());
              }}
              ref={renameTrigger}
            >
              Renomear
            </button>
            <button
              className="text-button danger-action"
              ref={deleteTrigger}
              disabled={locked}
              onClick={() => {
                setAction("delete");
                requestAnimationFrame(() => deleteConfirm.current?.focus());
              }}
            >
              Excluir
            </button>
          </div>
        </>
      )}
    </article>
  );
}
export function FavoritesPanel({
  favorites,
  loading,
  error,
  onRefresh,
  onAnalysis,
  ...actions
}: FavoriteActions & {
  favorites: Favorite[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  onAnalysis: () => void;
}) {
  const refreshButton = useRef<HTMLButtonElement>(null);
  return (
    <section
      className="favorites-panel"
      aria-labelledby="favorites-heading"
      aria-busy={loading || actions.busy}
    >
      <div className="favorites-heading">
        <div>
          <h2 id="favorites-heading">Consultas favoritas</h2>
          <p>
            Consultas pessoais com lojas e datas fixas. Você pode conferir um
            cálculo registrado ou consultar a base atual novamente.
          </p>
        </div>
        <button
          className="text-button"
          disabled={loading || actions.busy}
          onClick={onRefresh}
          ref={refreshButton}
        >
          Recarregar favoritos
        </button>
      </div>
      {loading && (
        <p role="status">
          <span className="spinner" /> Carregando favoritos…
        </p>
      )}
      {error && (
        <p className="notice warning" role="status">
          {error} Use Recarregar favoritos para tentar novamente.
        </p>
      )}
      {!loading && !error && favorites.length === 0 && (
        <div className="favorites-empty">
          <p>Nenhuma consulta favorita disponível.</p>
          <p>
            Faça uma consulta e use “Salvar consulta favorita” no cálculo que
            deseja guardar.
          </p>
          <button
            className="primary-button"
            disabled={actions.busy}
            onClick={onAnalysis}
          >
            Ir para análises
          </button>
        </div>
      )}
      {favorites.length > 0 && (
        <div className="favorites-list">
          {favorites.map((favorite) => (
            <FavoriteItem
              key={favorite.id}
              favorite={favorite}
              returnFocusTo={refreshButton}
              {...actions}
              busy={actions.busy || loading}
            />
          ))}
        </div>
      )}
    </section>
  );
}
