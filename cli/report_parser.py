

def add_report_module(subparsers, common):
    report_parser = subparsers.add_parser("report", parents=[common], help="Generate a report based on the analysis data using an AI model")
    
    report_parser.add_argument("--module", choices=["static"], default="static", help="Module report")
    report_parser.add_argument("--profile", choices=["local-report", "openai-report"], default="local-report", help="AI model")

    report_parser.set_defaults(func="run_report")
    
   

