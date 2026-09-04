import type { FeatureFlag } from '../api/types.ts'
import { featureFlagHash, navigate } from '../router.ts'
import { ENVIRONMENT_LABELS, formatDate, formatEnabled, formatRollout } from '../shared/format.ts'

interface Props {
  flags: FeatureFlag[]
  selectedId: string | null
}

export function FeatureFlagTable({ flags, selectedId }: Props) {
  return (
    <table aria-label="Feature flags">
      <thead>
        <tr>
          <th scope="col">Key</th>
          <th scope="col">Description</th>
          <th scope="col">Environment</th>
          <th scope="col">State</th>
          <th scope="col" className="numeric">
            Rollout
          </th>
          <th scope="col">Updated</th>
        </tr>
      </thead>
      <tbody>
        {flags.map((flag) => {
          const selected = flag.id === selectedId
          return (
            <tr
              key={flag.id}
              className={`selectable env-${flag.environment}`}
              aria-selected={selected}
              onClick={() => navigate(featureFlagHash(flag.id))}
            >
              <td>
                <a
                  className="row-link"
                  href={featureFlagHash(flag.id)}
                  aria-current={selected ? 'true' : undefined}
                >
                  {flag.key}
                </a>
              </td>
              <td className="description">{flag.description}</td>
              <td>
                <span className={`tag tag-${flag.environment}`}>
                  {ENVIRONMENT_LABELS[flag.environment]}
                </span>
              </td>
              <td>
                <span className={`tag tag-${flag.enabled ? 'enabled' : 'disabled'}`}>
                  {formatEnabled(flag.enabled)}
                </span>
              </td>
              <td className="numeric">{formatRollout(flag.rollout_percent)}</td>
              <td>
                <time dateTime={flag.updated_at}>{formatDate(flag.updated_at)}</time>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
