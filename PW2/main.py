import argparse
import time
from pipelines import phase1_image

def main():
    parser = argparse.ArgumentParser(description="Octree Color Quantizer")
    parser.add_argument('--phase', type=int, choices=[1, 2, 3, 4], required=True, 
                        help="Which phase of the project to run")
    parser.add_argument('--input', type=str, required=True, 
                        help="Path to file OR directory")
    parser.add_argument('--colors', type=int, default=16, 
                        help="Target number of colors")
    
    args = parser.parse_args()
    start_time = time.time()

    match args.phase:
        case 1:
            print(f"--- Starting Phase 1 ---")
            print(f"Input: {args.input} | Target Colors: {args.colors}")
            phase1_image.process_target(args.input, args.colors)
        case 2:
            print("Phase 2 is not implemented yet.")
        case 3:
            print("Phase 3 is not implemented yet.")
        case 4:
            print("Phase 4 is not implemented yet.")

    elapsed_time = time.time() - start_time
    print(f"\n--- Total Execution Time: {elapsed_time:.4f} seconds ---")

if __name__ == "__main__":
    main()