import os
import sys
import random
import shutil
from pathlib import Path

def main():
    base_dir = Path(__file__).parent
    
    # Find all terrain folders that have a 'rotations' subfolder
    terrain_folders = sorted([
        d for d in base_dir.iterdir()
        if d.is_dir() and (d / "rotations").exists()
    ])
        
    for terrain_dir in terrain_folders:
        folder_name = terrain_dir.name
        rotations_dir = terrain_dir / "rotations"
        
        # Get all CSV segment files
        csv_files = sorted([f for f in os.listdir(rotations_dir) if f.endswith(".csv")])
        
        if len(csv_files) < 4:
            print(f"  [{folder_name}] Skipping - only {len(csv_files)} segments (need at least 4)")
            continue
        
        # Set up ml/train and ml/test directories, clearing them first
        train_dir = terrain_dir / "ml" / "train"
        test_dir = terrain_dir / "ml" / "test"
        
        if train_dir.exists():
            shutil.rmtree(train_dir)
        if test_dir.exists():
            shutil.rmtree(test_dir)
            
        train_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Randomly pick 3 for test, rest for train
        random.shuffle(csv_files)
        test_files = csv_files[:3]
        train_files = csv_files[3:]
        
        for f in test_files:
            shutil.copy2(rotations_dir / f, test_dir / f)
            
        for f in train_files:
            shutil.copy2(rotations_dir / f, train_dir / f)
        
        print(f"  [{folder_name}] {len(train_files)} train, {len(test_files)} test")
    
    print("Train/test split complete.")

if __name__ == "__main__":
    main()
