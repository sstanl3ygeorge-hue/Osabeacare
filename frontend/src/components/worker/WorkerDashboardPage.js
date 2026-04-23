export default function WorkerDashboardPage({
  header,
  nextAction,
  readinessChecklist,
  agreements,
  documents,
  training,
  checks,
  support,
  children,
}) {
  return (
    <div className="min-h-screen bg-slate-50">
      {header}
      <main className="mx-auto flex max-w-4xl flex-col gap-4 px-4 py-4">
        {nextAction}
        {readinessChecklist}
        {agreements}
        {documents}
        {training}
        {checks}
        {support}
        {children}
      </main>
    </div>
  );
}
