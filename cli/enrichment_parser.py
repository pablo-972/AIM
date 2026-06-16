

def add_enrichment_module(subparsers, common):
    enrichment_parser = subparsers.add_parser("enrichment", parents=[common], help="Generate a enrichment based on the analysis data using an AI model")

    enrichment_parser.add_argument("--profile", choices=["local-enrichment", "openai-enrichment"], default="local-enrichment", help="AI model")
    
    enrichment_parser.set_defaults(func="run_enrichment")