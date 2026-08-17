import type { ExportWarning } from "../exportWarnings";

interface Props {
  warnings: ExportWarning[];
  canContinue: boolean;
  onClose: () => void;
  onContinue: () => void;
}

export function ExportWarningsDialog({
  warnings,
  canContinue,
  onClose,
  onContinue,
}: Props) {
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="modal-card export-warnings-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="export-warnings-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <h2 id="export-warnings-title">Lưu ý trước khi xuất ZIP</h2>
        <p>Các query dưới đây cần được kiểm tra lại.</p>
        <div className="warnings-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Tên query</th>
                <th>Lưu ý</th>
              </tr>
            </thead>
            <tbody>
              {warnings.map((warning) => (
                <tr key={warning.fileName}>
                  <td>{warning.fileName}</td>
                  <td>
                    {warning.notes.length === 1 ? (
                      warning.notes[0]
                    ) : (
                      <ul>
                        {warning.notes.map((note) => (
                          <li key={note}>{note}</li>
                        ))}
                      </ul>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="modal-actions">
          <button className="button secondary" type="button" onClick={onClose}>
            {canContinue ? "Hủy" : "Đóng"}
          </button>
          {canContinue && (
            <button
              className="button primary"
              type="button"
              onClick={onContinue}
            >
              Vẫn xuất ZIP
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
