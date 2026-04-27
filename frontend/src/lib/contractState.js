const CONTRACT_STATE_TO_STATUS = {
  awaiting_worker_signature: 'pending_signature',
  awaiting_company_countersignature: 'signed',
  fully_executed: 'fully_executed',
  rejected: 'rejected',
  action_required: 'action_required',
  superseded: 'superseded',
};

const REISSUE_STATUSES = new Set(['rejected', 'rejected_reopen_required', 'action_required', 'superseded']);

const toMs = (value) => {
  if (!value) return 0;
  const parsed = Date.parse(String(value));
  return Number.isNaN(parsed) ? 0 : parsed;
};

export function resolveLatestContractState(contractLike, options = {}) {
  const contractEligibility = options.contractEligibility || null;
  const source = contractLike || {};

  const rawState = String(
    source.contract_state || source.lifecycle_state || source.state || ''
  ).trim().toLowerCase();
  const rawStatus = String(
    source.active_contract_status ||
    source.latest_contract_status ||
    source.contract_status ||
    source.latest_status ||
    source.status ||
    ''
  ).trim().toLowerCase();

  const status = CONTRACT_STATE_TO_STATUS[rawState] || rawStatus;
  const normalizedState = rawState || (status === 'pending_signature' ? 'awaiting_worker_signature' : '');
  const isAwaitingWorkerSignature = status === 'pending_signature' || normalizedState === 'awaiting_worker_signature';
  const canSign = status === 'pending_signature'
    ? Boolean(source.can_sign ?? contractEligibility?.can_sign)
    : Boolean(contractEligibility?.can_sign ?? source.can_sign);
  const hasPendingSignableContract =
    isAwaitingWorkerSignature && (canSign || Boolean(contractEligibility?.contract_override?.active_pending_contract_id));

  return {
    status,
    state: normalizedState,
    isAwaitingWorkerSignature,
    canSign,
    hasPendingSignableContract,
    needsReissue: !isAwaitingWorkerSignature && REISSUE_STATUSES.has(status),
  };
}

export function getLatestActiveContract(agreements, options = {}) {
  const contractRows = Array.isArray(agreements)
    ? agreements.filter((agreement) => agreement?.id === 'contract_acceptance')
    : [];
  if (!contractRows.length) return null;

  const ranked = [...contractRows].sort((a, b) => {
    const aTs = Math.max(
      toMs(a?.active_contract_generated_at),
      toMs(a?.contract_generated_at),
      toMs(a?.generated_at),
      toMs(a?.updated_at),
      toMs(a?.created_at),
    );
    const bTs = Math.max(
      toMs(b?.active_contract_generated_at),
      toMs(b?.contract_generated_at),
      toMs(b?.generated_at),
      toMs(b?.updated_at),
      toMs(b?.created_at),
    );
    return bTs - aTs;
  });

  const latest = ranked[0];
  return {
    ...latest,
    __contractResolution: resolveLatestContractState(latest, options),
  };
}

