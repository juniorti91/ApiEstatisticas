import { useEffect } from "react";
import { X } from "lucide-react";

/**
 * Modal genérico reutilizável (overlay + painel), no mesmo estilo visual
 * dos cards do dashboard. Fecha com ESC, clique fora, ou botão X.
 */
export default function Modal({ open, onClose, title, children, widthClass = "max-w-2xl" }) {
  useEffect(() => {
    if (!open) return undefined;
    function onKeyDown(e) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-2 sm:px-4 py-4 sm:py-8"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className={`w-full ${widthClass} max-h-full overflow-y-auto overflow-x-hidden bg-panel border border-border rounded-xl shadow-2xl p-4 sm:p-6`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4 sticky top-0 bg-panel">
          <h2 className="text-base font-semibold text-slate-100">{title}</h2>
          <button onClick={onClose} className="text-muted hover:text-slate-200 shrink-0">
            <X size={18} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
