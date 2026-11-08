import { z } from "zod"

export const alertsTickSchema = z.object({
  type: z.literal("alerts_tick"),
  mode: z.string().optional(),
  total: z.number(),
  critical: z.number(),
  high: z.number(),
  is_stale: z.boolean().optional(),
  as_of_week_start_date: z.string().optional(),
})

export type AlertsTick = z.infer<typeof alertsTickSchema>

export function parseAlertsTick(raw: unknown): AlertsTick | null {
  const out = alertsTickSchema.safeParse(raw)
  return out.success ? out.data : null
}
