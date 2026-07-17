// imports extra:
import { useState } from "react";

function PayModal({ booking, token, onClose, onDone }) {
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [voucherUrl, setVoucherUrl] = useState("");
  const [reference, setReference] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");

  const submit = async () => {
    setErr("");
    if (!amount) { setErr("Amount required"); return; }
    setSubmitting(true);
    try {
      const r = await fetch(`http://127.0.0.1:8000/api/bookings/${booking.id}/pay`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          amount: Number(amount),
          currency,
          voucher_url: voucherUrl || null,
          reference: reference || null,
        })
      });
      if (!r.ok) throw new Error(await r.text());
      await r.json();
      onDone(); // refresca lista
      onClose();
    } catch (e) {
      setErr(String(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal d-block" tabIndex="-1" role="dialog" style={{background:"rgba(0,0,0,.3)"}}>
      <div className="modal-dialog"><div className="modal-content">
        <div className="modal-header">
          <h5 className="modal-title">Payment voucher</h5>
          <button className="btn-close" onClick={onClose} />
        </div>
        <div className="modal-body">
          <div className="mb-2">
            <label className="form-label">Amount</label>
            <input className="form-control" type="number" min="0" step="0.01"
                   value={amount} onChange={e=>setAmount(e.target.value)} />
          </div>
          <div className="mb-2">
            <label className="form-label">Currency</label>
            <input className="form-control" value={currency} onChange={e=>setCurrency(e.target.value)} />
          </div>
          <div className="mb-2">
            <label className="form-label">Voucher image URL</label>
            <input className="form-control" placeholder="https://..."
                   value={voucherUrl} onChange={e=>setVoucherUrl(e.target.value)} />
          </div>
          <div className="mb-2">
            <label className="form-label">Reference</label>
            <input className="form-control" value={reference} onChange={e=>setReference(e.target.value)} />
          </div>
          {err && <div className="text-danger small">{err}</div>}
        </div>
        <div className="modal-footer">
          <button className="btn btn-light" onClick={onClose} disabled={submitting}>Close</button>
          <button className="btn btn-primary" onClick={submit} disabled={submitting}>Submit</button>
        </div>
      </div></div>
    </div>
  );
}
