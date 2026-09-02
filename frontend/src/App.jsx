import { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

function Metric({ label, value, detail }) {
  return (
    <section className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </section>
  );
}

function StatusBadge({ value }) {
  return <span className={`badge badge-${String(value).toLowerCase()}`}>{value}</span>;
}

function App() {
  const [payments, setPayments] = useState([]);
  const [selectedPayment, setSelectedPayment] = useState(null);
  const [recovery, setRecovery] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadPayments() {
    try {
      setError("");

      const response = await fetch(`${API_BASE}/api/v1/payments`);

      if (!response.ok) {
        throw new Error(`Payment API returned ${response.status}`);
      }

      const data = await response.json();
      setPayments(Array.isArray(data) ? data : data.payments || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadRecovery(paymentId) {
    try {
      setError("");

      const response = await fetch(
        `${API_BASE}/api/v1/recovery/plan/${paymentId}`,
      );

      if (!response.ok) {
        throw new Error(`Recovery API returned ${response.status}`);
      }

      const data = await response.json();
      setSelectedPayment(paymentId);
      setRecovery(data);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadPayments();
  }, []);

  const failed = payments.filter(
    (payment) => String(payment.status).toLowerCase() === "failed",
  );

  const pending = payments.filter(
    (payment) => String(payment.status).toLowerCase() === "pending",
  );

  const failedValue = failed.reduce(
    (total, payment) => total + Number(payment.amount || 0),
    0,
  );

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">PAYMENTOPS AI</p>
          <h1>Recovery Control Plane</h1>
          <p className="subtitle">
            Payment reliability, risk intelligence and controlled revenue
            recovery.
          </p>
        </div>

        <div className="system-status">
          <span className="status-dot" />
          Control plane online
        </div>
      </header>

      <div className="content">
        {error && <div className="error">{error}</div>}

        <div className="metrics">
          <Metric
            label="Payments"
            value={payments.length}
            detail="Observed payment events"
          />
          <Metric
            label="Failed"
            value={failed.length}
            detail="Requires recovery analysis"
          />
          <Metric
            label="Pending"
            value={pending.length}
            detail="Requires state verification"
          />
          <Metric
            label="Failed value"
            value={`₹${failedValue.toLocaleString("en-IN")}`}
            detail="Gross failed payment value"
          />
        </div>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">PAYMENT EVENTS</p>
              <h2>Recovery queue</h2>
            </div>

            <button onClick={loadPayments}>Refresh</button>
          </div>

          {loading ? (
            <div className="empty">Loading payment events…</div>
          ) : payments.length === 0 ? (
            <div className="empty">No payment events available.</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Payment</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Failure</th>
                    <th>Latency</th>
                    <th />
                  </tr>
                </thead>

                <tbody>
                  {payments.map((payment) => (
                    <tr key={payment.payment_id}>
                      <td>
                        <strong>{payment.payment_id}</strong>
                        <small>
                          {payment.connector} · {payment.method}
                        </small>
                      </td>
                      <td>
                        {payment.currency}{" "}
                        {Number(payment.amount).toLocaleString("en-IN")}
                      </td>
                      <td>
                        <StatusBadge value={payment.status} />
                      </td>
                      <td>{payment.failure_code || "—"}</td>
                      <td>{payment.latency_ms ?? "—"} ms</td>
                      <td>
                        <button
                          className="action-button"
                          onClick={() =>
                            loadRecovery(payment.payment_id)
                          }
                        >
                          Analyze
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {recovery && selectedPayment && (
          <section className="panel recovery-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">RECOVERY INTELLIGENCE</p>
                <h2>{selectedPayment}</h2>
              </div>
              <StatusBadge value={recovery.policy.decision} />
            </div>

            <div className="recovery-grid">
              <div className="decision-card">
                <span>Next best action</span>
                <strong>{recovery.next_best_action.action}</strong>
                <p>{recovery.next_best_action.reason}</p>
              </div>

              <div className="decision-card">
                <span>Risk</span>
                <strong>
                  {Math.round(recovery.incident.risk_score * 100)}%
                </strong>
                <p>
                  {recovery.incident.severity} ·{" "}
                  {recovery.incident.root_cause}
                </p>
              </div>

              <div className="decision-card">
                <span>Policy</span>
                <strong>{recovery.policy.decision}</strong>
                <p>
                  {recovery.policy.reason_codes.join(" · ")}
                </p>
              </div>

              <div className="decision-card">
                <span>Execution</span>
                <strong>{recovery.execution.status}</strong>
                <p>{recovery.execution.message}</p>
              </div>
            </div>

            <div className="audit-row">
              <span>
                Audit: <strong>{recovery.audit.audit_id}</strong>
              </span>
              <span>
                Idempotency:{" "}
                <strong>{recovery.policy.idempotency_key}</strong>
              </span>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}

export default App;
