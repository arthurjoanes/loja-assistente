import { Brand, Icon } from "@/components/icon";
import { useEffect, useRef, type KeyboardEvent, type RefObject } from "react";
import type { Conversation, Session } from "@/lib/contracts";

type SidebarProps = {
  user: Session["user"];
  history: Conversation[];
  conversationId: string | null;
  view: "assistant" | "operations";
  mobileMenu: boolean;
  returnFocusTo: RefObject<HTMLButtonElement | null>;
  locked: boolean;
  onClose: () => void;
  onNewAnalysis: () => void;
  onShowAnalysis: () => void;
  onShowOperations: () => void;
  onOpenConversation: (id: string) => void;
  onSignOut: () => void;
};

export function AnalysisSidebar({
  user,
  history,
  conversationId,
  view,
  mobileMenu,
  returnFocusTo,
  locked,
  onClose,
  onNewAnalysis,
  onShowAnalysis,
  onShowOperations,
  onOpenConversation,
  onSignOut,
}: SidebarProps) {
  const navigation = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!mobileMenu) return;
    const trigger = returnFocusTo.current;
    navigation.current?.querySelector<HTMLButtonElement>("button")?.focus();
    return () => {
      trigger?.focus();
    };
  }, [mobileMenu, returnFocusTo]);

  function handleNavigationKey(event: KeyboardEvent<HTMLElement>) {
    if (!mobileMenu) return;
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key !== "Tab") return;
    const controls = Array.from(
      navigation.current?.querySelectorAll<HTMLElement>(
        "button:not(:disabled), summary",
      ) ?? [],
    ).filter((control) => control.getBoundingClientRect().width > 0);
    const first = controls[0];
    const last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  }
  const initials = user.name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0])
    .join("");
  return (
    <aside
      ref={navigation}
      className={"sidebar " + (mobileMenu ? "sidebar-open" : "")}
      aria-label="Navegação principal"
      role={mobileMenu ? "dialog" : undefined}
      aria-modal={mobileMenu || undefined}
      onKeyDown={handleNavigationKey}
    >
      <div className="sidebar-brand">
        <Brand />
        <button
          className="icon-button mobile-only"
          onClick={() => onClose()}
          aria-label="Fechar menu"
        >
          <Icon name="close" />
        </button>
      </div>
      <button
        className="new-conversation"
        onClick={onNewAnalysis}
        disabled={locked}
      >
        <Icon name="plus" size={19} />
        Nova análise
      </button>
      <nav className="main-nav">
        <button
          className={view === "assistant" ? "active" : ""}
          aria-current={view === "assistant" ? "page" : undefined}
          onClick={() => {
            onShowAnalysis();
            onClose();
          }}
        >
          <Icon name="spark" size={19} />
          Análises
        </button>
        <button
          className={view === "operations" ? "active" : ""}
          aria-current={view === "operations" ? "page" : undefined}
          onClick={() => void onShowOperations()}
          disabled={locked}
        >
          <Icon name="chart" size={19} />
          Atendimentos
        </button>
      </nav>
      <details className="history-menu">
        <summary>
          <Icon name="clock" size={14} /> Histórico{" "}
          <span>{history.length} conversas</span>
          <Icon name="chevron" size={12} />
        </summary>
        <nav className="history-list" aria-label="Histórico pessoal">
          {history.length === 0 ? (
            <p className="history-empty">Nenhuma conversa</p>
          ) : (
            history.map((item) => (
              <button
                key={item.id}
                title={item.title}
                aria-current={
                  conversationId === item.id && view === "assistant"
                    ? "page"
                    : undefined
                }
                className={
                  conversationId === item.id && view === "assistant"
                    ? "selected"
                    : ""
                }
                onClick={() => void onOpenConversation(item.id)}
                disabled={locked}
              >
                <Icon name="list" size={15} />
                <span className="history-entry">
                  <span className="history-title">{item.title}</span>
                  <time
                    className="history-date"
                    dateTime={item.created_at}
                    title={new Date(item.created_at).toLocaleString("pt-BR", {
                      timeZoneName: "short",
                    })}
                  >
                    {new Date(item.created_at).toLocaleString("pt-BR", {
                      dateStyle: "short",
                      timeStyle: "short",
                    })}
                  </time>
                </span>
              </button>
            ))
          )}
        </nav>
      </details>
      <div className="sidebar-bottom">
        <div className="profile">
          <span className="profile-avatar">{initials}</span>
          <span className="profile-name">
            <strong>{user.name}</strong>
            <small>
              {user.role === "supervisor" ? "Supervisor" : "Gerente"} ·{" "}
              {user.organization.name}
            </small>
          </span>
          <button
            className="icon-button"
            title="Sair"
            aria-label="Sair"
            onClick={() => void onSignOut()}
            disabled={locked}
          >
            <Icon name="logout" size={18} />
          </button>
        </div>
      </div>
    </aside>
  );
}
