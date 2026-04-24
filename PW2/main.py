import argparse
import time
from pipelines import phase1_image

def main():
    parser = argparse.ArgumentParser(description="Octree Color Quantizer")
    parser.add_argument('--phase', type=int, choices=[1, 2, 3, 4], required=True, 
                        help="Which phase of the project to run")
    parser.add_argument('--stats', action='store_true', 
                        help="Generate statistics charts (only for phase 1)")
    
    parser.add_argument('--input', type=str, 
                        help="Path to file OR directory")
    parser.add_argument('--colors', type=int, default=8, 
                        help="Target number of colors")
    
    args = parser.parse_args()
    match args.phase:
        case 1:
            print(f"--- Starting Phase 1 ---")
            if args.input:
                print(f"Input: {args.input} | Target Colors: {args.colors}")
                phase1_image.process_target(args.input, args.colors)

            if args.stats:
                print(f"--- Generating Statistics ---")
                phase1_image.generate_statistics_charts()
                
        case 2:
            print("Phase 2 is not implemented yet.")
        case 3:
            print("Phase 3 is not implemented yet.")
        case 4:
            print("Phase 4 is not implemented yet.")

if __name__ == "__main__":
    main()