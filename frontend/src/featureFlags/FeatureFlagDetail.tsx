import type { FeatureFlag } from '../api/types.ts'
import { DetailsTable, Row, Timestamp } from '../shared/DetailsTable.tsx'
import { ENVIRONMENT_LABELS, formatEnabled, formatRollout } from '../shared/format.ts'

export function FeatureFlagDetail({ flag }: { flag: FeatureFlag }) {
  return (
    <DetailsTable caption="Feature flag fields">
      <Row label="Flag id">
        <code>{flag.id}</code>
      </Row>
      <Row label="Key">
        <code>{flag.key}</code>
      </Row>
      <Row label="Description">{flag.description}</Row>
      <Row label="Environment">
        <span className={`tag tag-${flag.environment}`}>{ENVIRONMENT_LABELS[flag.environment]}</span>
        {flag.environment === 'production' && (
          <span className="muted"> (synthetic; no real system is controlled)</span>
        )}
      </Row>
      <Row label="State">
        <span className={`tag tag-${flag.enabled ? 'enabled' : 'disabled'}`}>
          {formatEnabled(flag.enabled)}
        </span>
      </Row>
      <Row label="Rollout">{formatRollout(flag.rollout_percent)}</Row>
      <Row label="Last updated">
        <Timestamp value={flag.updated_at} />
      </Row>
    </DetailsTable>
  )
}
