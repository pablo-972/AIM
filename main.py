from cli.base_parser import build_parser
from orchestrator.orchestrator import Orchestrator


def print_banner():
    print(r"""                                          
     ▄▄     ▄▄▄▄▄▄  ▄▄▄     ▄▄▄    
   ▄█▀▀█▄  █▀ ██     ███▄ ▄███    
   ██  ██     ██     ██ ▀█▀ ██  
   ██▀▀██     ██     ██     ██  
 ▄ ██  ██     ██     ██     ██   
 ▀██▀  ▀█▄█ ▄▄██▄▄ ▀██▀     ▀██▄  
""")
    

def main():
    parser = build_parser()
    args = parser.parse_args()

    if hasattr(args, "validator"):
        args.validator(args)

    orchestrator = Orchestrator(args)
    orchestrator.run()


if __name__ == "__main__":
    print_banner()
    main()
