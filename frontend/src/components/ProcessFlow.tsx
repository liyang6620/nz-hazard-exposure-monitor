import { Building2, CheckCircle2, Radio, Waves } from "lucide-react";

const steps = [
  {
    icon: Radio,
    title: "GeoNet earthquake",
    body: "A revised M4.0+ event enters the monitor.",
  },
  {
    icon: Waves,
    title: "Shaking footprint",
    body: "Official intensity data is preferred; a preliminary estimate fills the gap.",
  },
  {
    icon: Building2,
    title: "Exposure overlay",
    body: "H3 cells connect shaking with buildings and 2023 population.",
  },
  {
    icon: CheckCircle2,
    title: "Approved briefing",
    body: "An analyst checks the evidence before a briefing is published.",
  },
];

export function ProcessFlow() {
  return (
    <ol className="process-flow">
      {steps.map(({ icon: Icon, title, body }, index) => (
        <li key={title}>
          <span className="step-number">{index + 1}</span>
          <Icon size={20} aria-hidden="true" />
          <div>
            <strong>{title}</strong>
            <p>{body}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
