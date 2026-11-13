// AI contribution: 50% or more AI-generated
import { useEffect, useState } from "react";

import { montrealDate } from "./confirmFormat";

/** Refresh day labels while open and when staff return to the window. */
export function usePickupClock() {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const refresh = () => {
      const current = new Date();
      setNow((previous) => (montrealDate(previous) === montrealDate(current) ? previous : current));
    };

    const interval = window.setInterval(refresh, 30_000);
    window.addEventListener("focus", refresh);

    return () => {
      window.clearInterval(interval);
      window.removeEventListener("focus", refresh);
    };
  }, []);

  return [now, setNow] as const;
}
