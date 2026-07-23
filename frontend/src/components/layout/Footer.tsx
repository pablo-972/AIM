function Footer() {
  const columns = [
    {
      title: "Getting started",
      href: "/docs/getting-started",
      links: [
        { label: "Configuration", href: "/docs/getting-started/configuration" },
        { label: "Deployment", href: "/docs/getting-started/deployment" },
        { label: "Malware lab", href: "/docs/getting-started/malware-lab" },
        { label: "Software agents", href: "/docs/getting-started/software-agents" },
      ],
    },
    {
      title: "Phases",
      href: "/docs/phases",
      links: [
        { label: "Static", href: "/docs/phases/static" },
        { label: "Dynamic", href: "/docs/phases/dynamic" },
        { label: "Enrichment", href: "/docs/phases/enrichment" },
        { label: "Reversing", href: "/docs/phases/reversing" },
        { label: "Report", href: "/docs/phases/report" },
      ],
    },
    {
      title: "Tools",
      href: "/docs/tools",
      links: [
        { label: "Static", href: "/docs/tools/static" },
        { label: "Dynamic", href: "/docs/tools/dynamic" },
        { label: "Reversing", href: "/docs/tools/reversing" },
      ],
    },
    {
      title: "Project",
      href: "/docs/architecture",
      links: [
        { label: "Architecture", href: "/docs/architecture" },
        { label: "AI", href: "/docs/ai" },
        { label: "Troubleshooting", href: "/docs/troubleshooting" },
      ],
    },
  ];

  return (
    <footer className="border-t border-line bg-page">
      <div className="mx-auto grid w-full max-w-7xl justify-items-center gap-5 px-5 py-5 sm:grid-cols-2 sm:px-8 lg:grid-cols-4 lg:px-10">
        {columns.map((column) => (
          <div key={column.title} className="text-left">
            <h2 className="text-sm font-bold text-ink">
              <a className="hover:text-pink-500" href={column.href}>
                {column.title}
              </a>
            </h2>
            <ul className="mt-2 space-y-1.5 text-[0.8125rem] text-muted">
              {column.links.map((link) => (
                <li key={link.href}>
                  <a className="hover:text-pink-500" href={link.href}>
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </footer>
  );
}

export default Footer;
