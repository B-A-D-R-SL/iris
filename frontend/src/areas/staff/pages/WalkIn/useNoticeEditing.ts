// AI contribution: 50% or more AI-generated
/** Which adults' saved notices are being replaced, and keeping a newly saved notice (US-18). */
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  decisionSummaryQueryKey,
  noticesQueryKey,
  type RecordedNotice,
} from "../../../../features/households/noticeApi";

export function useNoticeEditing(householdId: string) {
  const queryClient = useQueryClient();
  // Approval waits until each notice being replaced is saved or cancelled.
  const [replacing, setReplacing] = useState<ReadonlySet<string>>(new Set());

  const setMemberReplacing = (memberId: string, on: boolean) =>
    setReplacing((current) => {
      const next = new Set(current);
      if (on) next.add(memberId);
      else next.delete(memberId);
      return next;
    });

  const keepNotice = (notice: RecordedNotice) => {
    queryClient.setQueryData<RecordedNotice[]>(noticesQueryKey(householdId), (list = []) => [
      ...list.filter((entry) => entry.member !== notice.member),
      notice,
    ]);
    // A new notice changes what the decision would use.
    void queryClient.invalidateQueries({ queryKey: decisionSummaryQueryKey(householdId) });
  };

  return { replacing, setMemberReplacing, keepNotice };
}
