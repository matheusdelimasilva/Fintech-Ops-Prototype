// Mirrors backend/app/schemas.py. Keep in sync by hand; the backend is the source of truth.

export type Role = 'support_agent' | 'operations_manager' | 'admin'
export type RefundStatus = 'pending' | 'approved' | 'rejected' | 'escalated'
export type RiskLevel = 'low' | 'medium' | 'high'
export type PaymentStatus = 'captured' | 'settled' | 'disputed'
export type Environment = 'staging' | 'production'
export type AuditAction =
  | 'refund.approved'
  | 'refund.rejected'
  | 'refund.escalated'
  | 'feature_flag.updated'
export type EntityType = 'refund' | 'feature_flag'
export type RefundAction = 'approve' | 'reject' | 'escalate'

export interface DemoUser {
  id: string
  display_name: string
  role: Role
}

export interface Policy {
  approval_limit_cents: number | null
  can_edit_staging_flags: boolean
  can_edit_production_flags: boolean
  can_escalate_refunds: boolean
}

export interface Session {
  user: DemoUser
  policy: Policy
  available_users: DemoUser[]
  identity_note: string
}

export interface Refund {
  id: string
  customer_name: string
  customer_reference: string
  transaction_reference: string
  amount_cents: number
  currency: string
  payment_status: PaymentStatus
  refund_status: RefundStatus
  risk_level: RiskLevel
  reason_code: string
  created_at: string
  updated_at: string
  last_action: AuditAction | null
  last_action_by: string | null
  last_action_reason: string | null
  last_action_at: string | null
  allowed_actions: RefundAction[]
}

export interface FeatureFlag {
  id: string
  key: string
  description: string
  environment: Environment
  enabled: boolean
  rollout_percent: number
  updated_at: string
  /** Server-computed for the requesting user. Hints only: PATCH re-checks both. */
  can_edit: boolean
  requires_confirmation: boolean
}

/** Body of PATCH /api/feature-flags/{id}. Omit a field to leave it unchanged; never send null. */
export interface FeatureFlagPatch {
  enabled?: boolean
  rollout_percent?: number
  reason: string
  confirm_production?: boolean
}

export interface FeatureFlagListFilters {
  environment?: Environment
}

export type Snapshot = Record<string, unknown>

export interface AuditEvent {
  id: string
  occurred_at: string
  actor_user_id: string
  actor_display_name: string
  actor_role: Role
  action: AuditAction
  entity_type: EntityType
  entity_id: string
  before_state: Snapshot
  after_state: Snapshot
  reason: string
}

export interface RefundListFilters {
  search?: string
  status?: RefundStatus
  risk_level?: RiskLevel
}
