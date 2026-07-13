from cli.base_parser import build_parser


def print_banner() -> None:
    print(r"""                                          
     ▄▄     ▄▄▄▄▄▄  ▄▄▄     ▄▄▄    
   ▄█▀▀█▄  █▀ ██     ███▄ ▄███    
   ██  ██     ██     ██ ▀█▀ ██  
   ██▀▀██     ██     ██     ██  
 ▄ ██  ██     ██     ██     ██   
 ▀██▀  ▀█▄█ ▄▄██▄▄ ▀██▀     ▀██▄  
""")
    

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if hasattr(args, "validator") and args.validator is not None:
        args.validator(args)

    from core.orchestrator.orchestrator import Orchestrator
    orchestrator = Orchestrator(args)
    orchestrator.run()


if __name__ == "__main__":
    print_banner()
    main()
