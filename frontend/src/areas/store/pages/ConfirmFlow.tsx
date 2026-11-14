// AI contribution: 50% or more AI-generated
import type { ScannerStatus } from "../components/PickupScanner";
import { DoneStep, ReviewStep, ScanStep } from "./ConfirmSteps";
import type { DayLabels, Language } from "./confirmFormat";
import type { ConfirmFlowState } from "./useConfirmPickup";

type FlowProps = {
  flow: ConfirmFlowState;
  camera: ScannerStatus;
  codeFieldId: string;
  language: Language;
  dayLabels: DayLabels;
  onCamera: (status: ScannerStatus) => void;
};

function ScanBranch({ flow, camera, codeFieldId, language, onCamera }: FlowProps) {
  const code = flow.step.kind === "scan" ? flow.step.code : "";
  const error = flow.step.kind === "scan" ? flow.step.error : null;
  return (
    <ScanStep
      code={code}
      error={error}
      camera={camera}
      busy={flow.busy}
      codeFieldId={codeFieldId}
      language={language}
      onCamera={onCamera}
      onDetected={flow.onDetected}
      onCodeChange={flow.setScanCode}
      onLookup={() => flow.requestLookup(code)}
    />
  );
}

function ReviewBranch({ flow, language, dayLabels }: FlowProps) {
  if (flow.step.kind !== "review") return null;
  const pickup = flow.step.pickup;
  return (
    <ReviewStep
      pickup={pickup}
      now={flow.now}
      language={language}
      dayLabels={dayLabels}
      busy={flow.busy}
      error={flow.confirmError}
      onConfirm={() => flow.confirmPickup(pickup)}
      onCancel={flow.resetScan}
    />
  );
}

/** Picks scan, review, or done from the confirm hook state. */
export function ConfirmFlow(props: FlowProps) {
  if (props.flow.step.kind === "scan") return <ScanBranch {...props} />;
  if (props.flow.step.kind === "review") return <ReviewBranch {...props} />;
  return (
    <DoneStep
      pickup={props.flow.step.pickup}
      now={props.flow.now}
      language={props.language}
      dayLabels={props.dayLabels}
      onAgain={props.flow.resetScan}
    />
  );
}
