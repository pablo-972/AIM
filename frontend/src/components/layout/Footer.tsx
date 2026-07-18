function Footer() {
  return (
    <footer className="border-t border-line bg-panel">
      <div className="mx-auto grid w-full max-w-7xl gap-8 px-5 py-8 sm:grid-cols-2 sm:px-8 lg:px-10">
        <div>
          <h2 className="text-sm font-semibold uppercase text-ink">Tools, Phases</h2>
          <ul className="mt-3 space-y-2 text-sm text-muted">
            <li>Static analysis</li>
            <li>Dynamic analysis</li>
            <li>AI inference</li>
            <li>Enrichment and reporting</li>
          </ul>
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase text-ink">Documentation</h2>
          <ul className="mt-3 space-y-2 text-sm text-muted">
            <li>Dynamic setup</li>
            <li>Model profiles</li>
            <li>Analysis artifacts</li>
            <li>API reference</li>
          </ul>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
