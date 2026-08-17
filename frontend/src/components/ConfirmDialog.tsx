interface Props {
  title: string;
  message: string;
  confirming: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmDialog({
  title,
  message,
  confirming,
  onCancel,
  onConfirm,
}: Props) {
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onCancel}>
      <section
        className="modal-card confirmation-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirmation-title"
        aria-describedby="confirmation-message"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <h2 id="confirmation-title">{title}</h2>
        <p id="confirmation-message">{message}</p>
        <div className="modal-actions">
          <button
            className="button secondary"
            type="button"
            onClick={onCancel}
            disabled={confirming}
          >
            Hủy
          </button>
          <button
            className="button danger-button"
            type="button"
            onClick={onConfirm}
            disabled={confirming}
          >
            {confirming ? "Đang xóa…" : "Xóa"}
          </button>
        </div>
      </section>
    </div>
  );
}
