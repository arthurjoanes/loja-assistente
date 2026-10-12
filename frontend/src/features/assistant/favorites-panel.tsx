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
  const renameTrigger = useRef<HTMLButtonElement>(null);
  const deleteTrigger = useRef<HTMLButtonElement>(null);
  const renameInput = useRef<HTMLInputElement>(null);
  const deleteConfirm = useRef<HTMLButtonElement>(null);
  function cancelAction() {
    const target = action === "rename" ? renameTrigger : deleteTrigger;
    setAction(null);
    requestAnimationFrame(() => target.current?.focus());
  }
  const locked = busy || conflict;
  return (
    <article
      className="favorite-item"
      aria-labelledby={`favorite-${favorite.id}`}
      data-testid="favorite"
    >
      <h3 id={`favorite-${favorite.id}`}>{favorite.name}</h3>
      <p className="muted">
        Salva em{" "}
        <time dateTime={favorite.created_at}>
          {new Date(favorite.created_at).toLocaleString("pt-BR", {
            timeZone: "America/Sao_Paulo",
            dateStyle: "short",
            timeStyle: "short",
          })}
        </time>{" "}
        · revisão {favorite.revision}
      </p>
      <PlanScope plan={favorite.plan} stores={stores} />
      <p className="scope-guidance">
        Executar novamente usa estas datas absolutas e verifica seu acesso às
        lojas. Os filtros da próxima consulta não alteram o favorito.
      </p>
      {action === "rename" ? (
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            if (locked || !name.trim()) return;
            if (await onRename(favorite, name.trim())) cancelAction();
          }}
        >
          <label htmlFor={`rename-${favorite.id}`}>Novo nome do favorito</label>
          <input
            id={`rename-${favorite.id}`}
            ref={renameInput}
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={120}
            required
            disabled={locked}
          />
          <div className="favorite-actions">
            <button
              type="submit"
              className="primary-button"
              disabled={locked || !name.trim()}
            >
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
        <div className="favorite-actions">
          <button
            className="primary-button"
            disabled={locked}
            onClick={() => onRun(favorite)}
          >
            {busy ? "Aguarde…" : "Executar novamente"}
          </button>
          <button
            className="text-button"
            disabled={busy}
            onClick={() => onOpen(favorite)}
          >
            Abrir cálculo registrado
          </button>
          <button
            className="text-button"
            disabled={locked}
            onClick={() => {
              setName(favorite.name);
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
      )}
    </article>
  );
}
export function FavoritesPanel({
  favorites,
  loading,
  onRefresh,
  onAnalysis,
  ...actions
}: FavoriteActions & {
  favorites: Favorite[];
  loading: boolean;
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
            Planos pessoais com datas fixas. Cada nova execução gera um cálculo
            próprio no histórico.
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
      {loading ? (
        <p role="status">
          <span className="spinner" /> Carregando favoritos…
        </p>
      ) : favorites.length === 0 ? (
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
      ) : (
        <div className="favorites-list">
          {favorites.map((favorite) => (
            <FavoriteItem
              key={favorite.id}
              favorite={favorite}
              returnFocusTo={refreshButton}
              {...actions}
            />
          ))}
        </div>
      )}
    </section>
  );
}
