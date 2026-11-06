import { ArrowDownToLine, ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";

const questions = [
  {
    title: "How does the shaking threshold change exposure?",
    image: "event-overview.png",
    alt: "Event Overview report canvas with Kaikōura MMI map, four key figures and region ranking",
    finding:
      "In the Kaikōura replay, buildings at MMI 6+ total 78,564. Raising the threshold to MMI 7+ leaves 9,720.",
    page: "Event Overview",
  },
  {
    title: "Which places are exposed repeatedly?",
    image: "regional-exposure.png",
    alt: "Regional Exposure report canvas with New Zealand coastline, repeat exposure map and district ranking",
    finding:
      "Repeat exposure counts buildings in MMI 6+ cells across ten replays. It is repeated exposure, not a count of unique damaged buildings.",
    page: "Regional Exposure",
  },
  {
    title: "How does this event compare with past earthquakes?",
    image: "event-comparison.png",
    alt: "Event Comparison report canvas comparing buildings and people across ten historical replays",
    finding:
      "The ten fixed earthquakes use the same current building stock and 2023 population, so their exposure counts share one baseline.",
    page: "Event Comparison",
  },
  {
    title: "Is the data current and complete?",
    image: "data-health.png",
    alt: "Data Health report canvas showing last Azure run, failures, poison messages and event status",
    finding:
      "The 6 Nov snapshot captured a successful Azure run at 11:00 UTC. Poison messages include acceptance drills.",
    page: "Data Health",
  },
];

export default function WorkbenchPage() {
  return (
    <div className="page-container workbench-page">
      <header className="workbench-lead">
        <div>
          <h1>Analyst Workbench</h1>
          <p>
            The website records first-hour earthquake exposure. The workbench
            compares thresholds, repeated exposure and data health in Power BI
            Desktop.
          </p>
        </div>
        <a
          className="workbench-download"
          href="/workbench/nzhem-powerbi-report.pdf"
          download
        >
          <ArrowDownToLine size={18} aria-hidden="true" /> Download five-page
          PDF
        </a>
      </header>
      <p className="workbench-snapshot">
        Desktop snapshot: 6 Nov 2026. These report images and the PDF are a
        fixed export; the interactive version opens locally in Power BI Desktop.
      </p>
      {questions.map((question) => (
        <section className="workbench-question" key={question.page}>
          <div className="workbench-question-copy">
            <h2>{question.title}</h2>
            <p>{question.finding}</p>
            <span>{question.page}</span>
          </div>
          <a
            href={`/workbench/${question.image}`}
            target="_blank"
            rel="noreferrer"
          >
            <img
              src={`/workbench/${question.image}`}
              alt={question.alt}
              loading="lazy"
            />
            <span>
              Open report image <ArrowUpRight size={16} aria-hidden="true" />
            </span>
          </a>
        </section>
      ))}
      <p className="workbench-end">
        Event time exposure applies to live assessments. Historical replays use
        today&apos;s building stock and the 2023 Census. Read the{" "}
        <Link to="/method">method and limitations</Link> before comparing them.
      </p>
    </div>
  );
}
