import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import RiskBadge from '../components/RiskBadge'
import { CaseOutcomeBadge, CaseStatusBadge } from '../components/CaseStatusBadge'
import { ErrorPanel, LoadingPanel } from '../components/States'
import VerificationChecklist from '../components/VerificationChecklist'
import AuditTrail from '../components/AuditTrail'
import api from '../services/api'
import useApi from '../hooks/useApi'
import { useRole } from '../hooks/useRole'
import { humanDate, orDash, riskStyle } from '../utils/format'

/**
 * One investigation case.
 *
 * The screen where the officer actually works: the signals that caused the
 * case, the checklist generated from those signals, the remarks and evidence
 * references recorded against each one, and the trail of everything that has
 * been done. The engine's assessment is shown alongside, never replaced by, the
 * officer's own record.
 */
export default function CaseDetail() {
  const { caseId } = useParams()
  const { roleKey } = useRole()
  const { data, error, loading, reload } = useApi(
    (opts) => api.case(caseId, opts),
    [caseId, roleKey],
  )

  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState(null)

  if (loading) return <LoadingPanel label={`Loading case ${caseId}…`} rows={8} />
  if (error)
    return <ErrorPanel error={error} onRetry={reload} context={`GET /api/cases/${caseId}`} />

  const analysis = data.analysis
  const live = analysis?.risk
  const style = riskStyle(live?.risk_level || data.risk_level_at_open)
  const drift =
    live && data.risk_score_at_open != null
      ? Math.round(live.risk_score) - Math.round(data.risk_score_at_open)
      : null

  /** Run one mutating call, then refresh the whole case so the trail stays true. */
  async function act(fn) {
    setBusy(true)
    setActionError(null)
    try {
      await fn()
      reload()
    } catch (err) {
      setActionError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* -------------------------------------------------- header */}
      <div className="flex flex-wrap items-start gap-x-4 gap-y-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="tnum text-lg font-bold tracking-tight text-ink-900">{data.case_id}</h2>
            <CaseStatusBadge status={data.status} size="lg" />
            <CaseOutcomeBadge outcome={data.outcome} />
          </div>
          <p className="mt-0.5 text-[13px] text-ink-600">
            <Link to={`/projects/${data.project_id}`} className="link tnum font-semibold">
              {data.project_id}
            </Link>
            {analysis?.project_name ? ` · ${analysis.project_name}` : ''}
          </p>
          {data.status_meaning && (
            <p className="mt-0.5 max-w-2xl text-2xs leading-relaxed text-ink-500">
              {data.status_meaning}
            </p>
          )}
        </div>

        <div className="ml-auto flex items-center gap-4">
          <div className="text-right">
            <div className="label">Risk score now</div>
            <div className={`tnum text-2xl font-bold leading-none ${style.text}`}>
              {live ? Math.round(live.risk_score) : '—'}
            </div>
            <div className="mt-1">
              <RiskBadge level={live?.risk_level} size="sm" />
            </div>
          </div>

          <div className="border-l border-ink-200 pl-4 text-right">
            <div className="label">At case opening</div>
            <div className="tnum text-[15px] font-semibold text-ink-700">
              {data.risk_score_at_open != null ? Math.round(data.risk_score_at_open) : '—'}
            </div>
            <div className="mt-0.5 text-2xs text-ink-500">
              {drift === null
                ? '—'
                : drift === 0
                  ? 'Unchanged'
                  : `${drift > 0 ? '+' : ''}${drift} since opening`}
            </div>
          </div>
        </div>
      </div>

      {actionError && (
        <ErrorPanel
          error={actionError}
          onRetry={() => setActionError(null)}
          context={`Case ${data.case_id}`}
        />
      )}

      {/* -------------------------------------------------- case facts */}
      <section className="panel">
        <div className="panel-header">
          <h3 className="panel-title">Case record</h3>
          <span className="text-2xs text-ink-500">
            Opened {humanDate(data.created_at)} · last updated {humanDate(data.updated_at)}
          </span>
        </div>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 p-4 md:grid-cols-4">
          <Field label="Opened by" value={data.opened_by} sub={data.opened_role} />
          <Field label="Assigned to" value={data.assigned_to} sub={data.assigned_role} />
          <Field label="District" value={data.district} sub={data.state} />
          <Field
            label="Signal at opening"
            value={data.primary_risk_at_open}
            sub={data.risk_level_at_open}
          />
        </dl>
        {data.outcome && (
          <div className="border-t border-ink-200 bg-ink-50 px-4 py-3">
            <div className="label">Recorded outcome</div>
            <div className="mt-0.5 text-[13px] font-semibold text-ink-900">{data.outcome}</div>
            {data.outcome_remark && (
              <p className="mt-1 text-[13px] leading-relaxed text-ink-700">{data.outcome_remark}</p>
            )}
          </div>
        )}
      </section>

      {/* -------------------------------------------------- actions */}
      <CaseActions data={data} busy={busy} act={act} />

      {/* -------------------------------------------------- checklist */}
      <VerificationChecklist
        caseId={data.case_id}
        items={data.checklist || []}
        summary={data.checklist_summary}
        note={data.checklist_note}
        canVerify={Boolean(data.permissions?.['case.verify']) && data.status !== 'CLOSED'}
        busy={busy}
        onUpdate={(itemKey, body) => act(() => api.updateChecklistItem(data.case_id, itemKey, body))}
      />

      {/* -------------------------------------------------- audit trail */}
      <AuditTrail events={data.audit_trail || []} />

      <p className="max-w-3xl text-2xs leading-relaxed text-ink-500">{data.notice}</p>
    </div>
  )
}

function Field({ label, value, sub }) {
  return (
    <div className="min-w-0">
      <dt className="label">{label}</dt>
      <dd className="field-value truncate">{orDash(value)}</dd>
      {sub && <dd className="truncate text-2xs text-ink-400">{sub}</dd>}
    </div>
  )
}

/**
 * The moves available on this case.
 *
 * Only what the acting role may actually do is offered, and the list of onward
 * statuses comes from the API rather than being hardcoded here — the workflow
 * rules live in one place on the server, and this screen reflects them.
 */
function CaseActions({ data, busy, act }) {
  const perms = data.permissions || {}
  const [status, setStatus] = useState('')
  const [statusRemark, setStatusRemark] = useState('')
  const [assignee, setAssignee] = useState('')
  const [outcome, setOutcome] = useState('')
  const [outcomeRemark, setOutcomeRemark] = useState('')
  const [remark, setRemark] = useState('')
  const [reference, setReference] = useState('')

  const statuses = data.available_statuses || []
  const canStatus = Boolean(perms['case.status'] || perms['case.escalate'] || perms['case.close'])

  return (
    <section className="panel">
      <div className="panel-header">
        <h3 className="panel-title">Case actions</h3>
        <span className="text-2xs text-ink-500">
          Available to your role · every action is recorded in the trail below
        </span>
      </div>

      <div className="grid gap-4 p-4 md:grid-cols-2">
        {/* ---- status */}
        {canStatus && statuses.length > 0 && (
          <div>
            <label className="label" htmlFor="case-status">
              Move case to
            </label>
            <select
              id="case-status"
              className="input mt-1"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="">Select a status…</option>
              {statuses.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <input
              className="input mt-2"
              placeholder="Reason for the change (optional)"
              value={statusRemark}
              onChange={(e) => setStatusRemark(e.target.value)}
            />
            <button
              type="button"
              className="btn-primary mt-2"
              disabled={busy || !status}
              onClick={() =>
                act(async () => {
                  await api.setCaseStatus(data.case_id, status, statusRemark || null)
                  setStatus('')
                  setStatusRemark('')
                })
              }
            >
              Change status
            </button>
          </div>
        )}

        {/* ---- assignment */}
        {perms['case.assign'] && data.status !== 'CLOSED' && (
          <div>
            <label className="label" htmlFor="case-assignee">
              Assign to
            </label>
            <select
              id="case-assignee"
              className="input mt-1"
              value={assignee}
              onChange={(e) => setAssignee(e.target.value)}
            >
              <option value="">Select an officer…</option>
              {(data.assignable_users || []).map((u) => (
                <option key={u.username} value={u.username}>
                  {u.display_name} — {u.designation}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn-primary mt-2"
              disabled={busy || !assignee}
              onClick={() =>
                act(async () => {
                  await api.assignCase(data.case_id, assignee)
                  setAssignee('')
                })
              }
            >
              Assign case
            </button>
          </div>
        )}

        {/* ---- outcome */}
        {perms['case.verify'] && (
          <div>
            <label className="label" htmlFor="case-outcome">
              Record outcome
            </label>
            <select
              id="case-outcome"
              className="input mt-1"
              value={outcome}
              onChange={(e) => setOutcome(e.target.value)}
            >
              <option value="">Select the finding…</option>
              {(data.available_outcomes || []).map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
            <input
              className="input mt-2"
              placeholder="What was found, in your words"
              value={outcomeRemark}
              onChange={(e) => setOutcomeRemark(e.target.value)}
            />
            <button
              type="button"
              className="btn-primary mt-2"
              disabled={busy || !outcome}
              onClick={() =>
                act(async () => {
                  await api.setCaseOutcome(data.case_id, outcome, outcomeRemark || null)
                  setOutcome('')
                  setOutcomeRemark('')
                })
              }
            >
              Record outcome
            </button>
            <p className="mt-1.5 text-2xs leading-relaxed text-ink-500">
              The outcome is stored as recorded. This prototype has no learning pipeline, so it does
              not adjust any weight, threshold or future score.
            </p>
          </div>
        )}

        {/* ---- remark */}
        <div>
          <label className="label" htmlFor="case-remark">
            Add a remark
          </label>
          <textarea
            id="case-remark"
            className="input mt-1"
            rows={2}
            placeholder="Observation, correspondence, or a note for the file"
            value={remark}
            onChange={(e) => setRemark(e.target.value)}
          />
          <input
            className="input mt-2"
            placeholder="Evidence or file reference (optional)"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
          />
          <button
            type="button"
            className="btn-secondary mt-2"
            disabled={busy || !remark.trim()}
            onClick={() =>
              act(async () => {
                await api.addCaseRemark(data.case_id, remark, reference || null)
                setRemark('')
                setReference('')
              })
            }
          >
            Add remark
          </button>
        </div>
      </div>

      {!canStatus && !perms['case.assign'] && !perms['case.verify'] && (
        <p className="border-t border-ink-200 px-4 py-3 text-2xs leading-relaxed text-ink-500">
          Your role can read this case and add remarks, but cannot change its status, assign it or
          record its outcome. Those actions belong to the officer responsible for the verification.
        </p>
      )}
    </section>
  )
}
