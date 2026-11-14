// AI contribution: 50% or more AI-generated
import type { Pickup, PickupFailed } from "../../../features/reservations/pickupApi";

export type ConfirmStep =
  | { kind: "scan"; code: string; error: PickupFailed | null }
  | { kind: "review"; pickup: Pickup }
  | { kind: "done"; pickup: Pickup };
